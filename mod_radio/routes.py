from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash, abort, Response
from datetime import datetime
import os
import io
from pydub import AudioSegment

from mod_auth.utils import login_required, admin_required
from .audio_utils import listar_audios
from mod_radio.audio_cache import obter_cache, atualizar_cache
from mod_config.models import carregar_radios_config, ConfigSistema, ConfigGoogleDrive
from mod_config.google_drive_utils import build_drive_service

bp_radio = Blueprint("radio", __name__, template_folder="templates")

# -------------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------------
def get_radios_config():
    """Carrega o dicionário de rádios a partir da configuração."""
    return carregar_radios_config()


# -------------------------------------------------------------------------
# SELECIONAR RÁDIO
# -------------------------------------------------------------------------
@bp_radio.route('/radio')
@login_required
def select_radio():
    radios_cfg = get_radios_config()
    return render_template('select_radio.html', radios=radios_cfg)


# -------------------------------------------------------------------------
# LISTAR ÁUDIOS (LOCAL + DRIVE)
# -------------------------------------------------------------------------
@bp_radio.route('/radio/<radio_key>')
@login_required
def selecionar_radio(radio_key):
    """
    Exibe a lista de áudios da rádio selecionada.
    Suporta rádios locais e rádios do Google Drive (busca recursiva em subpastas).
    """
    radios_cfg = get_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for('radio.select_radio'))

    data_str = request.args.get('data')
    hora_ini = request.args.get('hora_ini')
    hora_fim = request.args.get('hora_fim')
    page = int(request.args.get('page', 1))

    # Detectar se é rádio vinculada ao Google Drive
    if "[Google Drive]" in radio.get("pasta_base", "") or radio.get("tipo_pasta") == "drive":
        try:
            config = ConfigGoogleDrive.get()
            if not config:
                flash("Configuração do Google Drive não encontrada.", "warning")
                return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[])

            service = build_drive_service(config)

            # Busca o ID da pasta do Drive no banco
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).resolve().parents[1] / "usuarios.db"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT drive_folder_id FROM tb_radios WHERE chave=?", (radio_key,)).fetchone()
            conn.close()

            folder_id = row["drive_folder_id"] if row else None
            if not folder_id:
                flash("Pasta do Drive não configurada para esta rádio.", "warning")
                return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[])

            # --- busca recursiva ---
            def listar_arquivos_drive_recursivo(folder_id, extensoes=(".mp3", ".wav")):
                encontrados = []
                try:
                    query = f"'{folder_id}' in parents and trashed=false"
                    results = service.files().list(
                        q=query,
                        fields="files(id, name, mimeType, size, modifiedTime)",
                        orderBy="modifiedTime desc"
                    ).execute()
                    for f in results.get("files", []):
                        mime = f.get("mimeType", "")
                        nome = f.get("name", "")
                        if mime == "application/vnd.google-apps.folder":
                            encontrados.extend(listar_arquivos_drive_recursivo(f["id"], extensoes))
                        elif nome.lower().endswith(extensoes):
                            encontrados.append(f)
                except Exception as e:
                    print(f"❌ Erro ao listar subpastas do Drive: {e}")
                return encontrados

            drive_files = listar_arquivos_drive_recursivo(folder_id)
            audios = []
            for f in drive_files:
                nome = f.get("name")
                modificado = f.get("modifiedTime")
                tamanho = int(f.get("size", 0)) / 1024 if f.get("size") else 0
                audios.append({
                    "nome": nome,
                    "datahora": datetime.strptime(modificado, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y %H:%M:%S"),
                    "tamanho": f"{tamanho:,.0f} KB",
                    "caminho": f"https://drive.google.com/uc?id={f['id']}&export=download"
                })

            total = len(audios)
            por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
            inicio = (page - 1) * por_pagina
            fim = inicio + por_pagina
            pagina_audios = audios[inicio:fim]
            total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

            return render_template(
                "lista_audios.html",
                radio={'key': radio_key, **radio},
                audios=pagina_audios,
                pagina_atual=page,
                total_paginas=total_paginas,
                total=total,
                filtros={'data': data_str or '', 'hora_ini': hora_ini or '', 'hora_fim': hora_fim or ''},
                drive_mode=True
            )

        except Exception as e:
            print("❌ Erro ao listar Google Drive:", e)
            flash("Erro ao listar arquivos do Google Drive.", "danger")
            return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[], drive_mode=True)

    # Rádio local (mantém o comportamento anterior)
    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data = None

    todos_audios = obter_cache(radio_key)
    if not todos_audios:
        todos_audios = listar_audios(radio, data=data, hora_ini=hora_ini, hora_fim=hora_fim)

    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    por_pagina = max(1, min(100, por_pagina))
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
        drive_mode=False
    )

    radios_cfg = get_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for('radio.select_radio'))

    data_str = request.args.get('data')
    hora_ini = request.args.get('hora_ini')
    hora_fim = request.args.get('hora_fim')
    page = int(request.args.get('page', 1))

    # --- Detectar se é rádio vinculada ao Google Drive ---
    if "[Google Drive]" in radio.get("pasta_base", ""):
        try:
            config = ConfigGoogleDrive.get()
            if not config:
                flash("Configuração do Google Drive não encontrada.", "warning")
                return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[])

            service = build_drive_service(config)

            # Busca ID da pasta do Drive associada à rádio
            from mod_config.models import ConfigRadio
            from googleapiclient.errors import HttpError
            radio_db = None
            try:
                import sqlite3
                from pathlib import Path
                db_path = Path(__file__).resolve().parents[1] / "usuarios.db"
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                cur = conn.execute("SELECT drive_folder_id FROM tb_radios WHERE chave=?", (radio_key,))
                row = cur.fetchone()
                radio_db = dict(row) if row else None
                conn.close()
            except Exception as e:
                print("❌ Erro ao obter ID do Drive no banco:", e)

            folder_id = radio_db.get("drive_folder_id") if radio_db else None
            if not folder_id:
                flash("Pasta do Drive não configurada para esta rádio.", "warning")
                return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[])

            # --- Busca os arquivos da pasta do Drive ---
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false and mimeType contains 'audio/'",
                fields="files(id, name, mimeType, size, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()

            drive_files = results.get("files", [])
            audios = []
            for f in drive_files:
                nome = f.get("name")
                modificado = f.get("modifiedTime")
                tamanho = int(f.get("size", 0)) / 1024 if f.get("size") else 0
                audios.append({
                    "nome": nome,
                    "datahora": datetime.strptime(modificado, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y %H:%M:%S"),
                    "tamanho": f"{tamanho:,.0f} KB",
                    "caminho": f"https://drive.google.com/uc?id={f['id']}&export=download"
                })

            total = len(audios)
            por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
            inicio = (page - 1) * por_pagina
            fim = inicio + por_pagina
            pagina_audios = audios[inicio:fim]
            total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

            return render_template(
                "lista_audios.html",
                radio={'key': radio_key, **radio},
                audios=pagina_audios,
                pagina_atual=page,
                total_paginas=total_paginas,
                total=total,
                filtros={'data': data_str or '', 'hora_ini': hora_ini or '', 'hora_fim': hora_fim or ''},
                drive_mode=True
            )

        except Exception as e:
            print("❌ Erro ao listar Google Drive:", e)
            flash("Erro ao listar arquivos do Google Drive.", "danger")
            return render_template("lista_audios.html", radio={'key': radio_key, **radio}, audios=[], drive_mode=True)

    # --- Rádio local (mantém o comportamento anterior) ---
    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data = None

    todos_audios = obter_cache(radio_key)
    if not todos_audios:
        todos_audios = listar_audios(radio, data=data, hora_ini=hora_ini, hora_fim=hora_fim)

    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    por_pagina = max(1, min(100, por_pagina))
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
        drive_mode=False
    )

@bp_radio.route("/radio/audios/data")
@login_required
def audios_data():
    """
    EndPoint usado pelo front-end (AJAX) para listar áudios.
    Aceita: ?radio=<key>&data=YYYY-MM-DD&hora_ini=HH:MM&hora_fim=HH:MM&page=N
    Retorna JSON com paginação idêntica ao comportamento anterior.
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

    # paginação
    por_pagina = int(ConfigSistema.get().get("max_por_pagina", 20))
    por_pagina = max(1, min(100, por_pagina))

    # ----------------------------------------------------------
    # 1) RÁDIO DO GOOGLE DRIVE
    # ----------------------------------------------------------
    if radio.get("tipo_pasta") == "drive" or "[Google Drive]" in (radio.get("pasta_base") or ""):
        try:
            cfg_drive = ConfigGoogleDrive.get()
            if not cfg_drive:
                return jsonify({"ok": False, "erro": "Google Drive não configurado.", "audios": []}), 400

            service = build_drive_service(cfg_drive)

            # Busca o folder_id no banco
            import sqlite3
            from pathlib import Path
            db_path = Path(__file__).resolve().parents[1] / "usuarios.db"
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT drive_folder_id FROM tb_radios WHERE chave=?",
                (radio_key,)
            ).fetchone()
            conn.close()

            folder_id = row["drive_folder_id"] if row else None
            if not folder_id:
                return jsonify({"ok": False, "erro": "Pasta do Drive não vinculada a esta rádio.", "audios": []}), 400

            # lista arquivos de áudio no Drive
            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false and mimeType contains 'audio/'",
                fields="files(id, name, size, modifiedTime)",
                orderBy="modifiedTime desc"
            ).execute()

            files = results.get("files", [])
            itens = []
            for f in files:
                nome = f.get("name") or ""
                mod = f.get("modifiedTime")
                # formato ISO do Drive → dd/mm/yyyy HH:MM:SS
                try:
                    dt_txt = datetime.strptime(mod, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y %H:%M:%S")
                except Exception:
                    dt_txt = mod or ""
                tam_kb = 0
                if f.get("size"):
                    try:
                        tam_kb = int(int(f["size"]) / 1024)
                    except Exception:
                        tam_kb = 0

                itens.append({
                    "nome": nome,
                    "datahora": dt_txt,
                    "tamanho": f"{tam_kb:,} KB".replace(",", "."),
                    # link direto para download/stream (se arquivo for público/da sua conta)
                    "caminho": f"https://drive.google.com/uc?id={f['id']}&export=download",
                    "drive_id": f["id"],
                })

            total = len(itens)
            ini = (page - 1) * por_pagina
            fim = ini + por_pagina
            return jsonify({
                "ok": True,
                "audios": itens[ini:fim],
                "pagina_atual": page,
                "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
                "total": total
            })

        except Exception as e:
            print("❌ /radio/audios/data (Drive) erro:", e)
            return jsonify({"ok": False, "erro": "Falha ao listar no Google Drive.", "audios": []}), 500

    # ----------------------------------------------------------
    # 2) RÁDIO LOCAL (comportamento anterior)
    # ----------------------------------------------------------
    # filtros
    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            data = None

    # tenta ler do cache; se vazio, lista direto
    itens = obter_cache(radio_key) or listar_audios(radio, data=data, hora_ini=hora_ini, hora_fim=hora_fim)
    total = len(itens)
    ini = (page - 1) * por_pagina
    fim = ini + por_pagina

    return jsonify({
        "ok": True,
        "audios": itens[ini:fim],
        "pagina_atual": page,
        "total_paginas": max(1, (total + por_pagina - 1) // por_pagina),
        "total": total
    })

# -------------------------------------------------------------------------
# STREAM / PLAYER (LOCAL)
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
@bp_radio.route('/radio/<radio_key>/recortar', methods=['GET', 'POST'])
@login_required
def recortar_audio(radio_key):
    radios_cfg = get_radios_config()
    radio = radios_cfg.get(radio_key)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for('radio.select_radio'))

    if request.method == 'GET':
        caminho = request.args.get('path', '')
        if not caminho or not os.path.isfile(caminho):
            flash("Arquivo inválido.", "danger")
            return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))
        return render_template('recortar_audio.html', radio={'key': radio_key, **radio}, path=caminho)

    caminho = request.form.get('path')
    ini = request.form.get('inicio', '00:00')
    fim = request.form.get('fim', '00:30')

    if not caminho or not os.path.isfile(caminho):
        abort(403)

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
        return redirect(url_for('radio.selecionar_radio', radio_key=radio_key))


# -------------------------------------------------------------------------
# ATUALIZAÇÃO DE CACHE MANUAL
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
