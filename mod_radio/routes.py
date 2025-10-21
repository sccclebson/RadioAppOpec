from flask import (
    Blueprint, render_template, request, jsonify,
    send_file, redirect, url_for, flash, abort, Response
)
from datetime import datetime
import os
import io
import requests
from pydub import AudioSegment

from mod_auth.utils import login_required, admin_required
from mod_radio.audio_cache import obter_cache, atualizar_cache
from mod_radio.audio_utils import listar_audios
from mod_config.models import (
    carregar_radios_config,
    ConfigSistema,
    ConfigGoogleDrive
)
from mod_config.google_drive_utils import build_drive_service

bp_radio = Blueprint("radio", __name__, template_folder="templates")

# -------------------------------------------------------------------------
# 🔧 HELPERS
# -------------------------------------------------------------------------
def get_radios_config():
    """Carrega o dicionário de rádios a partir da configuração."""
    return carregar_radios_config()


# -------------------------------------------------------------------------
# 📻 SELECIONAR RÁDIO
# -------------------------------------------------------------------------
@bp_radio.route('/radio')
@login_required
def select_radio():
    radios_cfg = get_radios_config()
    return render_template('select_radio.html', radios=radios_cfg)


# -------------------------------------------------------------------------
# 🎧 LISTAR ÁUDIOS (LOCAL + DRIVE)
# -------------------------------------------------------------------------
@bp_radio.route('/radio/<radio_key>')
@login_required
def selecionar_radio(radio_key):
    radios_cfg = get_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for('radio.select_radio'))

    data_str = request.args.get('data')
    hora_ini = request.args.get('hora_ini')
    hora_fim = request.args.get('hora_fim')
    page = int(request.args.get('page', 1))

    todos_audios = obter_cache(radio_key)
    if not todos_audios:
        todos_audios = listar_audios(radio)

    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    total = len(todos_audios)
    inicio = (page - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_audios = todos_audios[inicio:fim]
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return render_template(
        "lista_audios.html",
        radio={'key': radio_key, **radio},
        audios=pagina_audios,
        pagina_atual=page,
        total_paginas=total_paginas,
        total=total,
        filtros={'data': data_str or '', 'hora_ini': hora_ini or '', 'hora_fim': hora_fim or ''},
    )


# -------------------------------------------------------------------------
# 📡 ENDPOINT AJAX – Listagem de áudios (LOCAL + DRIVE)
# -------------------------------------------------------------------------
@bp_radio.route("/radio/audios/data")
@login_required
def audios_data():
    """
    Endpoint usado pela interface AJAX para listar áudios.
    Suporta rádios locais e rádios Google Drive com cache híbrido.
    """
    radio_key = request.args.get("radio", "").strip()
    data_str = request.args.get("data") or ""
    hora_ini = request.args.get("hora_ini") or ""
    hora_fim = request.args.get("hora_fim") or ""
    page = int(request.args.get("page", 1))

    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        return jsonify({"ok": False, "erro": "Rádio não encontrada.", "audios": []}), 404

    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    por_pagina = max(1, min(100, por_pagina))

    # Tenta obter do cache
    audios = obter_cache(radio_key)
    if not audios:
        print(f"⚠️ Cache vazio para '{radio_key}', atualizando...")
        audios = atualizar_cache(radio_key)

    total = len(audios)
    ini = (page - 1) * por_pagina
    fim = ini + por_pagina
    pagina = audios[ini:fim]

    return jsonify({
        "ok": True,
        "audios": pagina,
        "pagina_atual": page,
        "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
        "total": total
    })


@bp_radio.route("/radio/play")
def play_audio():
    from flask import Response, send_file
    import io
    from googleapiclient.http import MediaIoBaseDownload
    import re

    caminho_raw = request.args.get("path")
    if not caminho_raw:
        return "Caminho inválido", 400

    # ☁️ --- STREAM GOOGLE DRIVE ---
    if "drive.google.com" in caminho_raw or "uc?id=" in caminho_raw:
        try:
            match = re.search(r"id=([a-zA-Z0-9_-]+)", caminho_raw)
            file_id = match.group(1) if match else None
            if not file_id:
                return "ID do arquivo inválido.", 400

            cfg_drive = ConfigGoogleDrive.get()
            if not cfg_drive:
                return "Configuração do Google Drive não encontrada.", 500

            service = build_drive_service(cfg_drive)
            request_drive = service.files().get_media(fileId=file_id)

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request_drive, chunksize=1024 * 256)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"⬇️ Download {int(status.progress() * 100)}%")

            buffer.seek(0)
            resp = Response(buffer, content_type="audio/mpeg")
            resp.headers["Content-Disposition"] = "inline; filename=drive_audio.mp3"
            resp.headers["Cache-Control"] = "no-store"
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp

        except Exception as e:
            print(f"❌ [DRIVE] Erro ao reproduzir do Drive: {e}")
            return f"Erro ao reproduzir do Drive: {e}", 500

    # 💽 --- STREAM LOCAL ---
    caminho_abs = os.path.abspath(caminho_raw)
    if not os.path.isfile(caminho_abs):
        return f"Arquivo não encontrado: {caminho_abs}", 404

    range_header = request.headers.get("Range", None)
    file_size = os.path.getsize(caminho_abs)

    def generate_local(file_path, start, length):
        with open(file_path, "rb") as f:
            f.seek(start)
            yield f.read(length)

    if range_header:
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0])
        end = int(byte_range[1]) if byte_range[1] else file_size - 1
        length = end - start + 1
        resp = Response(generate_local(caminho_abs, start, length), status=206, mimetype="audio/mpeg")
        resp.headers.add("Content-Range", f"bytes {start}-{end}/{file_size}")
        resp.headers.add("Accept-Ranges", "bytes")
        resp.headers.add("Content-Length", str(length))
    else:
        resp = send_file(caminho_abs, mimetype="audio/mpeg", conditional=True)

    resp.headers.add("Cache-Control", "no-store")
    resp.headers.add("Access-Control-Allow-Origin", "*")
    return resp


# -------------------------------------------------------------------------
# ✂️ RECORTE DE ÁUDIO (LOCAL)
# -------------------------------------------------------------------------
@bp_radio.route('/radio/<radio_key>/recortar', methods=['GET', 'POST'])
@login_required
def recortar_audio(radio_key):
    import io
    from googleapiclient.http import MediaIoBaseDownload

    radios_cfg = get_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for('radio.select_radio'))

    caminho = request.args.get('path') or request.form.get('path')
    if not caminho:
        flash("Caminho inválido.", "danger")
        return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))

    # ☁️ --- ARQUIVO DO GOOGLE DRIVE ---
    if caminho.startswith("http"):
        try:
            import re
            match = re.search(r"id=([a-zA-Z0-9_-]+)", caminho)
            file_id = match.group(1) if match else None
            if not file_id:
                flash("ID do arquivo inválido.", "danger")
                return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))

            cfg_drive = ConfigGoogleDrive.get()
            if not cfg_drive:
                flash("Configuração do Google Drive não encontrada.", "warning")
                return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))

            service = build_drive_service(cfg_drive)

            # Baixa o áudio do Drive em memória
            buffer = io.BytesIO()
            request_drive = service.files().get_media(fileId=file_id)
            downloader = MediaIoBaseDownload(buffer, request_drive, chunksize=1024 * 256)
            done = False
            while not done:
                status, done = downloader.next_chunk()
                if status:
                    print(f"⬇️ [Recorte] Download {int(status.progress() * 100)}%")

            buffer.seek(0)
            # Guarda em sessão temporária (sem gravar no disco)
            session['drive_temp_audio'] = buffer.getvalue()
            session['drive_temp_name'] = f"drive_{file_id}.mp3"

            # Redireciona para tela de recorte (simula arquivo local)
            return render_template('recortar_audio.html', radio={'key': radio_key, **radio}, path=caminho, drive_mode=True)

        except Exception as e:
            print(f"❌ [DRIVE] Erro ao preparar recorte: {e}")
            flash("Erro ao preparar recorte do Google Drive.", "danger")
            return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))

    # 💽 --- ARQUIVO LOCAL ---
    if request.method == 'GET':
        if not os.path.isfile(caminho):
            flash("Arquivo inválido.", "danger")
            return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))
        return render_template('recortar_audio.html', radio={'key': radio_key, **radio}, path=caminho, drive_mode=False)

    # --- POST (APLICAR RECORTE) ---
    ini = request.form.get('inicio', '00:00')
    fim = request.form.get('fim', '00:30')

    def to_ms(hhmmss):
        parts = [int(p) for p in hhmmss.split(':')]
        if len(parts) == 2:
            m, s = parts
            return (m * 60 + s) * 1000
        elif len(parts) == 3:
            h, m, s = parts
            return (h * 3600 + m * 60 + s) * 1000
        return 0

    try:
        if caminho.startswith("http"):
            # Recupera o áudio em memória
            audio_bytes = session.get('drive_temp_audio')
            if not audio_bytes:
                flash("Sessão expirada. Baixe novamente o arquivo do Drive.", "warning")
                return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))

            audio = AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        else:
            audio = AudioSegment.from_file(caminho)

        cut = audio[to_ms(ini):to_ms(fim)]
        buf = io.BytesIO()
        cut.export(buf, format="mp3")
        buf.seek(0)

        nome_saida = session.get('drive_temp_name', os.path.basename(caminho))
        saida = f"recorte_{ini.replace(':','')}-{fim.replace(':','')}_{nome_saida}"

        return send_file(buf, as_attachment=True, download_name=saida, mimetype="audio/mpeg")

    except Exception as e:
        print(f"❌ Erro ao recortar: {e}")
        flash(f"Erro ao recortar áudio: {e}", "danger")
        return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))


# -------------------------------------------------------------------------
# 🔄 ATUALIZAÇÃO MANUAL DE CACHE
# -------------------------------------------------------------------------
@bp_radio.route('/radio/<radio_key>/atualizar-cache')
@admin_required
def atualizar_cache_manual(radio_key):
    try:
        atualizar_cache(radio_key)
        flash(f"Cache da rádio '{radio_key}' atualizado com sucesso.", "success")
        print(f"🔄 [ADMIN] Cache manual solicitado para {radio_key}")
    except Exception as e:
        flash(f"Erro ao atualizar cache da rádio '{radio_key}': {e}", "danger")
    return redirect(url_for('admin.status_cache'))
