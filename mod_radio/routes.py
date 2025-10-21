from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, abort, Response
from datetime import datetime
import os
import io
from pydub import AudioSegment

from mod_auth.utils import login_required, admin_required
from .audio_utils import listar_audios
from mod_radio.audio_cache import obter_cache, atualizar_cache
from mod_config.models import carregar_radios_config, ConfigSistema

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
# AJAX: LISTAGEM JSON
# -------------------------------------------------------------------------
@bp_radio.route("/radio/audios/data")
@login_required
def audios_data():
    radio_key = request.args.get("radio", "").strip()
    data_str = request.args.get("data") or ""
    hora_ini = request.args.get("hora_ini") or ""
    hora_fim = request.args.get("hora_fim") or ""
    page = int(request.args.get("page", 1))

    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        return jsonify({"ok": False, "erro": "Rádio não encontrada.", "audios": []}), 404

    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data = None

    # adiciona chave da rádio antes de chamar listar_audios()
    # Ajuste no trecho que chama listar_audios()
    radio["chave"] = radio_key
    todos_audios = obter_cache(radio_key)
    if not todos_audios:
        # sempre garantir o radio_key dentro do dict
        radio["chave"] = radio_key
        todos_audios = listar_audios(radio, data=data, hora_ini=hora_ini, hora_fim=hora_fim)


    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    total = len(todos_audios)
    ini = (page - 1) * por_pagina
    fim = ini + por_pagina

    return jsonify({
        "ok": True,
        "audios": todos_audios[ini:fim],
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

    # --- Modo GET: abre tela de recorte ---
    if request.method == "GET":
        caminho = request.args.get("path", "")
        caminho = unquote(caminho).replace("/", "\\")
        print(f"🎬 [RECORTE] Caminho recebido: {caminho}")

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

    # --- Modo POST: processa recorte ---
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
        audio = AudioSegment.from_file(caminho)
        cut = audio[to_ms(ini):to_ms(fim)]
        buf = io.BytesIO()
        cut.export(buf, format="mp3")
        buf.seek(0)
        filename = os.path.basename(caminho)
        saida = f"recorte_{ini.replace(':','')}-{fim.replace(':','')}_{filename}"
        return send_file(buf, as_attachment=True, download_name=saida, mimetype="audio/mpeg")
    except Exception as e:
        flash(f"Erro ao recortar: {e}", "danger")
        return redirect(url_for("radio.selecionar_radio", radio_key=radio_key))


# -------------------------------------------------------------------------
# ATUALIZAÇÃO DE CACHE MANUAL
# -------------------------------------------------------------------------
@bp_radio.route("/radio/<radio_key>/atualizar-cache")
@admin_required
def atualizar_cache_manual(radio_key):
    try:
        atualizar_cache(radio_key)
        flash(f"Cache da rádio '{radio_key}' atualizado com sucesso.", "success")
        print(f"🔄 [ADMIN] Cache manual solicitado para {radio_key}")
    except Exception as e:
        flash(f"Erro ao atualizar cache da rádio '{radio_key}': {e}", "danger")
    return redirect(url_for("radio.select_radio"))
