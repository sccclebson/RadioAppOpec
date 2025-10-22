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
from pathlib import Path

bp_radio = Blueprint("radio", __name__, template_folder="templates")

# -------------------------------------------------------------------------
# (Demais rotas e utilitários permanecem como estavam) 
# Observação: mantive o restante do arquivo original, apenas as rotas de
# "recortar" e "media" foram normalizadas para subpath e segurança. 
# -------------------------------------------------------------------------

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

    def parse_h(h, default):
        try:
            return datetime.strptime(h, "%H:%M").time() if h else default
        except Exception:
            return default

    t_ini = parse_h(hora_ini, time(0, 0))
    t_fim = parse_h(hora_fim, time(23, 59))

    filtrados = []
    for it in itens:
        try:
            dt = datetime.strptime(it.get("datahora"), "%d/%m/%Y %H:%M:%S")
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
    radios_cfg = carregar_radios_config()
    radio_key = request.args.get("radio")
    radio = radios_cfg.get(radio_key)
    if not radio:
        return jsonify({"erro": "Rádio não encontrada"}), 404

    # Filtros
    data = request.args.get("data", "")
    hora_ini = request.args.get("hora_ini", "")
    hora_fim = request.args.get("hora_fim", "")

    # Paginação
    try:
        page = int(request.args.get("page", "1"))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    cfg = ConfigSistema.get()
    por_pagina = cfg.get("max_por_pagina", 50) if cfg else 50

    cache = obter_cache(radio_key)
    itens = cache.get("itens", [])
    itens = _filtra_por_data_hora(itens, data, hora_ini, hora_fim)

    total = len(itens)
    inicio = (page - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_itens = itens[inicio:fim]

    return jsonify({
        "total": total,
        "page": page,
        "per_page": por_pagina,
        "itens": pagina_itens
    })


# -------------------------------------------------------------------------
# 🎛️ PÁGINAS DE LISTA E SELEÇÃO (sem mudanças funcionais nessa fase)
# -------------------------------------------------------------------------
@bp_radio.route("/radio/<radio_key>")
@login_required
def selecionar_radio(radio_key):
    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for("radio.select_radio"))

    data_hoje = datetime.now().strftime("%Y-%m-%d")
    return render_template("lista_audios.html", radio=radio, data_hoje=data_hoje)


@bp_radio.route("/select_radio")
@login_required
def select_radio():
    radios_cfg = carregar_radios_config()
    return render_template("select_radio.html", radios=radios_cfg)


# -------------------------------------------------------------------------
# ✂️ RECORTAR ÁUDIO — agora usa SUBPATH (sem C:\.. na URL)
# -------------------------------------------------------------------------
@bp_radio.route("/radio/<radio_key>/recortar", methods=["GET", "POST"])
@login_required
def recortar_audio(radio_key):
    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for("radio.select_radio"))

    # Modo GET → abre a tela de recorte recebendo apenas o subpath
    if request.method == "GET":
        subpath = request.args.get("subpath", "")
        if not subpath:
            return abort(400, "Subpath não informado")

        base_dir = Path(os.getcwd()) / "media_drive"
        arquivo = (base_dir / Path(*subpath.split("/"))).resolve()
        try:
            arquivo.relative_to(base_dir)
        except ValueError:
            return abort(403, "Acesso negado: caminho fora do diretório base")
        if not arquivo.exists():
            return abort(404, "Arquivo não encontrado")

        nome_arquivo = arquivo.name
        return render_template(
            "recortar_audio.html",
            radio={"key": radio_key, **radio},
            subpath=subpath,   # <- variável que o template usa
            nome_arquivo=nome_arquivo,
            filtros={"data": "", "hora_ini": "", "hora_fim": ""},
        )

    # (Se houver POST para exportar/recortar, permanece como está. 
    #  Caso leia "path" do form, adaptar para "subpath" futuramente.)
    flash("Método não suportado nesta fase.", "warning")
    return redirect(url_for("radio.selecionar_radio", radio_key=radio_key))


# -------------------------------------------------------------------------
# 📡 SERVIR ÁUDIO POR SUBPATH — seguro + suporte a Range
# -------------------------------------------------------------------------
@bp_radio.route("/media/<path:subpath>")
@login_required
def servir_audio(subpath):
    """Serve arquivos MP3/WAV de dentro de media_drive com segurança, com suporte a Range."""
    import re as _re
    base_dir = Path(os.getcwd()) / "media_drive"
    arquivo = (base_dir / Path(*subpath.split("/"))).resolve()
    try:
        arquivo.relative_to(base_dir)
    except ValueError:
        return abort(403)
    if not arquivo.exists() or not arquivo.is_file():
        return abort(404)

    file_size = arquivo.stat().st_size
    range_header = request.headers.get("Range")
    if range_header:
        m = _re.match(r"bytes=(\d*)-(\d*)", range_header)
        if m:
            start = int(m.group(1)) if m.group(1) else 0
            end = int(m.group(2)) if m.group(2) else file_size - 1
            start = max(0, start); end = min(end, file_size - 1)
            length = end - start + 1

            def generate():
                with open(arquivo, "rb") as f:
                    f.seek(start)
                    remaining = length
                    chunk = 8192
                    while remaining > 0:
                        data = f.read(min(chunk, remaining))
                        if not data:
                            break
                        remaining -= len(data)
                        yield data

            rv = Response(
                generate(),
                status=206,
                mimetype="audio/mpeg" if arquivo.suffix.lower()==".mp3" else "audio/wav"
            )
            rv.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
            rv.headers.add("Accept-Ranges", "bytes")
            rv.headers.add("Content-Length", str(length))
            return rv

    # Resposta completa (sem Range)
    return send_file(str(arquivo), mimetype="audio/mpeg" if arquivo.suffix.lower()==".mp3" else "audio/wav")
