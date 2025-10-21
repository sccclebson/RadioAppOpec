from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, abort, Response
from datetime import datetime
import os
import io
from pydub import AudioSegment

from mod_auth.utils import login_required, admin_required
from .audio_utils import listar_audios
from mod_radio.audio_cache import obter_cache, atualizar_cache
from mod_config.models import carregar_radios_config, ConfigSistema

from urllib.parse import unquote

bp_radio = Blueprint("radio", __name__, template_folder="templates")

# -------------------------------------------------------------------------
# SELEÇÃO DE RÁDIO
# -------------------------------------------------------------------------
@bp_radio.route("/radio")
@login_required
def select_radio():
    radios_cfg = carregar_radios_config()
    return render_template("select_radio.html", radios=radios_cfg)


# -------------------------------------------------------------------------
# LISTAGEM DE ÁUDIOS
# -------------------------------------------------------------------------
@bp_radio.route("/radio/<radio_key>")
@login_required
def selecionar_radio(radio_key):
    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for("radio.select_radio"))

    data_str = request.args.get("data")
    hora_ini = request.args.get("hora_ini")
    hora_fim = request.args.get("hora_fim")
    page = int(request.args.get("page", 1))

    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data = None

    # adiciona chave da rádio antes de chamar listar_audios()
    radio["chave"] = radio_key

    # tenta ler do cache
    todos_audios = obter_cache(radio_key)
    if not todos_audios:
        todos_audios = listar_audios(radio, data=data, hora_ini=hora_ini, hora_fim=hora_fim)

    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    total = len(todos_audios)
    inicio = (page - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_audios = todos_audios[inicio:fim]
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return render_template(
        "lista_audios.html",
        radio={"key": radio_key, **radio},
        audios=pagina_audios,
        pagina_atual=page,
        total_paginas=total_paginas,
        total=total,
        filtros={"data": data_str or "", "hora_ini": hora_ini or "", "hora_fim": hora_fim or ""},
    )


# -------------------------------------------------------------------------
# 🔊 API DE LISTAGEM DE ÁUDIOS (AJAX)
# -------------------------------------------------------------------------
from datetime import datetime, time

def _filtra_por_data_hora(itens, data_str, hora_ini, hora_fim):
    """Filtra uma lista de áudios (em cache) pelos campos de data e hora."""
    if not (data_str or hora_ini or hora_fim):
        return itens

    try:
        data_alvo = datetime.strptime(data_str, "%Y-%m-%d").date() if data_str else None
    except Exception:
        data_alvo = None

    try:
        t_ini = datetime.strptime(hora_ini, "%H:%M").time() if hora_ini else time(0, 0)
    except Exception:
        t_ini = time(0, 0)

    try:
        t_fim = datetime.strptime(hora_fim, "%H:%M").time() if hora_fim else time(23, 59)
    except Exception:
        t_fim = time(23, 59)

    filtrados = []
    for it in itens:
        try:
            dt = datetime.strptime(it.get("datahora", ""), "%d/%m/%Y %H:%M:%S")
        except Exception:
            continue

        if data_alvo and dt.date() != data_alvo:
            continue
        if not (t_ini <= dt.time() <= t_fim):
            continue

        filtrados.append(it)
    return filtrados


@bp_radio.route("/radio/audios/data")
@login_required
def audios_data():
    """Retorna lista de áudios (com paginação e filtros AJAX)."""
    from flask import request, jsonify

    radio_key = request.args.get("radio")
    data_str = request.args.get("data", "")
    hora_ini = request.args.get("hora_ini", "")
    hora_fim = request.args.get("hora_fim", "")
    page = int(request.args.get("page", 1))
    por_pagina = 50

    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        return jsonify({"ok": False, "msg": "Rádio não encontrada."})

    from mod_radio.audio_cache import obter_cache
    from mod_radio.audio_utils import listar_audios

    itens = obter_cache(radio_key)

    # 🔍 Se o cache estiver vazio, gera do zero
    if not itens:
        itens = listar_audios(
            {"pasta_base": radio.get("pasta_base"), "extensao": radio.get("extensao", ".mp3"), "nome": radio.get("nome", radio_key)},
            data=data_str or None, hora_ini=hora_ini or None, hora_fim=hora_fim or None
        )
    else:
        # ✅ Aplica filtro sobre cache existente
        if data_str or hora_ini or hora_fim:
            itens = _filtra_por_data_hora(itens, data_str, hora_ini, hora_fim)

    total = len(itens)
    ini = (page - 1) * por_pagina
    fim = ini + por_pagina

    print(f"🕒 [FILTRO] Rádio: {radio_key} | Data: {data_str or '-'} | {hora_ini or '--:--'} → {hora_fim or '--:--'} | {len(itens)} arquivos filtrados")

    return jsonify({
        "ok": True,
        "audios": itens[ini:fim],
        "pagina_atual": page,
        "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
        "total": total
    })



# -------------------------------------------------------------------------
# STREAM / PLAYER
# -------------------------------------------------------------------------
@bp_radio.route("/radio/play")
def play_audio():
    caminho_raw = request.args.get("path")
    if not caminho_raw:
        return "Caminho inválido", 400

    caminho_abs = os.path.abspath(caminho_raw)
    if not os.path.isfile(caminho_abs):
        return f"Arquivo não encontrado: {caminho_abs}", 404

    file_size = os.path.getsize(caminho_abs)
    range_header = request.headers.get("Range", None)

    def generate(file_path, start, length):
        with open(file_path, "rb") as f:
            f.seek(start)
            yield f.read(length)

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = end - start + 1
        resp = Response(generate(caminho_abs, start, length), status=206, mimetype="audio/mpeg")
        resp.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
        resp.headers.add("Accept-Ranges", "bytes")
        resp.headers.add("Content-Length", str(length))
    else:
        resp = send_file(caminho_abs, mimetype="audio/mpeg", conditional=True)

    resp.headers.add("Cache-Control", "no-store")
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp


# -------------------------------------------------------------------------
# RECORTE DE ÁUDIO
# -------------------------------------------------------------------------
@bp_radio.route("/radio/<radio_key>/recortar", methods=["GET", "POST"])
@login_required
def recortar_audio(radio_key):
    from urllib.parse import unquote

    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for("radio.select_radio"))

    # ==============================================================
    # MODO GET → abre a tela de recorte
    # ==============================================================
    if request.method == "GET":
        caminho_raw = request.args.get("path", "")
        caminho = unquote(caminho_raw).replace("/", "\\")
        print(f"🎬 [RECORTE] Caminho recebido (decodificado): {caminho}")

        # Se for um caminho relativo dentro da pasta sincronizada:
        if not os.path.isabs(caminho) and "[Google Drive]" in radio.get("pasta_base", ""):
            import pathlib
            MEDIA_DIR = pathlib.Path(os.getcwd()) / "media_drive"
            nome_radio = radio.get("nome", "").replace(" ", "_")
            caminho = str(MEDIA_DIR / nome_radio / caminho_raw)

        # Valida se o arquivo existe
        if not os.path.isfile(caminho):
            flash("Arquivo inválido ou não encontrado.", "danger")
            return redirect(url_for("radio.selecionar_radio", radio_key=radio_key))

        nome_arquivo = os.path.basename(caminho)
        return render_template(
            "recortar_audio.html",
            radio={"key": radio_key, **radio},
            path=caminho,
            nome_arquivo=nome_arquivo,
        )

    # ==============================================================
    # MODO POST → processa o recorte e faz download
    # ==============================================================
    caminho = request.form.get("path")
    ini = request.form.get("inicio", "00:00")
    fim = request.form.get("fim", "00:30")

    if not caminho or not os.path.isfile(caminho):
        abort(403)

    def to_ms(hhmmss):
        parts = [int(p) for p in hhmmss.split(":")]
        if len(parts) == 2:
            m, s = parts
            return (m * 60 + s) * 1000
        elif len(parts) == 3:
            h, m, s = parts
            return (h * 3600 + m * 60 + s) * 1000
        return 0

    try:
        print(f"✂️ [RECORTE] Recortando {caminho} ({ini} → {fim})...")
        audio = AudioSegment.from_file(caminho)
        cut = audio[to_ms(ini):to_ms(fim)]
        buf = io.BytesIO()
        cut.export(buf, format="mp3")
        buf.seek(0)

        filename = os.path.basename(caminho)
        saida = f"recorte_{ini.replace(':','')}-{fim.replace(':','')}_{filename}"
        print(f"✅ [RECORTE] Recorte concluído: {saida}")

        return send_file(
            buf,
            as_attachment=True,
            download_name=saida,
            mimetype="audio/mpeg"
        )
    except Exception as e:
        print(f"❌ [RECORTE] Erro ao recortar: {e}")
        flash(f"Erro ao recortar: {e}", "danger")
        return redirect(url_for("radio.selecionar_radio", radio_key=radio_key))


# -------------------------------------------------------------------------
# ATUALIZAÇÃO DE CACHE MANUAL
# -------------------------------------------------------------------------
@bp_radio.route('/radio/<radio_key>/atualizar-cache')
@admin_required
def atualizar_cache_manual(radio_key):
    from mod_config.models import carregar_radios_config
    radios_cfg = carregar_radios_config()
    radio_cfg = radios_cfg.get(radio_key)

    if not radio_cfg:
        flash(f"⚠️ Rádio '{radio_key}' não encontrada nas configurações.", "danger")
        return redirect(url_for("admin.status_cache"))

    print(f"💾 [CACHE] Usando pasta sincronizada local para '{radio_key}': {radio_cfg.get('pasta_base')}")
    atualizar_cache(radio_key, radio_cfg)
    flash(f"✅ Cache da rádio '{radio_cfg.get('nome', radio_key)}' atualizado com sucesso.", "success")

    # 🔁 Fica na mesma página de status
    print(f"✅ [ADMIN] Cache manual atualizado para '{radio_key}'.")
    return redirect(url_for('admin.status_cache'))


# -------------------------------------------------------------------------
# 🎵 ROTA PARA SERVIR ARQUIVOS DE ÁUDIO LOCAIS
# -------------------------------------------------------------------------
from flask import send_file, abort
from pathlib import Path

@bp_radio.route("/media/<path:subpath>")
@login_required
def servir_audio(subpath):
    """
    Serve arquivos MP3/WAV de dentro de media_drive com segurança.
    Exemplo: /media/Radio_Gralha/30-09-2025/20250930235551.mp3
    """
    base_dir = Path(os.getcwd()) / "media_drive"
    arquivo = base_dir / subpath

    if not arquivo.exists() or not arquivo.is_file():
        print(f"⚠️ [AUDIO] Arquivo não encontrado: {arquivo}")
        return abort(404)

    # Permite MP3/WAV
    ext = arquivo.suffix.lower()
    mime = "audio/mpeg" if ext == ".mp3" else "audio/wav"
    print(f"🎧 [AUDIO] Servindo: {arquivo}")
    return send_file(arquivo, mimetype=mime)
