from flask import Blueprint, render_template, request, jsonify, send_file, redirect, url_for, flash
from datetime import datetime
import os
from mod_auth.utils import login_required
from config import RADIOS_CONFIG
from .audio_utils import listar_audios
from pydub import AudioSegment
import io

bp_radio = Blueprint("radio", __name__, template_folder="templates")


# 🎙️ Selecionar rádio
@bp_radio.route("/radio")
@login_required
def select_radio():
    """Tela inicial: seleção de rádios disponíveis."""
    return render_template("select_radio.html", radios=RADIOS_CONFIG)


@bp_radio.route("/radio/audios/data")
@login_required
def lista_audios():
    """Listar áudios filtrados e paginados por data e hora."""
    data_str = request.args.get("data")
    hora_ini = request.args.get("hora_ini")
    hora_fim = request.args.get("hora_fim")
    page = int(request.args.get("page", 1))
    radio_key = request.args.get("radio", "clube")
    radio_cfg = RADIOS_CONFIG.get(radio_key)

    if not radio_cfg:
        return jsonify({"erro": "Rádio não encontrada"}), 400

    # Converte a data (se houver)
    data = None
    if data_str:
        try:
            data = datetime.strptime(data_str, "%Y-%m-%d").date()
        except ValueError:
            pass

    # 🔎 Busca com filtro
    audios = listar_audios(radio_cfg, data=data, hora_ini=hora_ini, hora_fim=hora_fim)
    total = len(audios)

    # 🧮 Paginação
    por_pagina = 20  # reduzido pra melhor performance
    inicio = (page - 1) * por_pagina
    fim = inicio + por_pagina
    pagina_audios = audios[inicio:fim]
    total_paginas = max(1, (total + por_pagina - 1) // por_pagina)

    return jsonify({
        "audios": pagina_audios,
        "pagina_atual": page,
        "total_paginas": total_paginas,
        "total_arquivos": total,
    })



# 🎧 Exibir lista de áudios da rádio selecionada
@bp_radio.route("/radio/<radio_id>")
@login_required
def selecionar_radio(radio_id):
    """Abre a página de listagem da rádio específica."""
    radio = RADIOS_CONFIG.get(radio_id)
    if not radio:
        flash("Rádio não encontrada.", "danger")
        return redirect(url_for("radio.select_radio"))

    data_hoje = datetime.now().strftime("%Y-%m-%d")
    return render_template("lista_audios.html", radio=radio, data_hoje=data_hoje)


# ▶️ Reproduzir áudio
@bp_radio.route("/radio/play")
@login_required
def play_audio():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "Arquivo não encontrado", 404
    return send_file(path, mimetype="audio/mpeg")


# ✂️ Tela de recorte de áudio
@bp_radio.route("/radio/recortar")
@login_required
def recortar_audio():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        flash("Arquivo não encontrado.", "danger")
        return redirect(url_for("radio.select_radio"))

    nome_arquivo = os.path.basename(path)
    return render_template("recortar_audio.html", path=path, nome_arquivo=nome_arquivo)


# 💾 Gera e faz download do recorte
@bp_radio.route("/radio/recortar/download", methods=["POST"])
@login_required
def recortar_download():
    path = request.form.get("path")
    inicio = float(request.form.get("inicio", 0))
    fim = float(request.form.get("fim", 10))

    if not path or not os.path.exists(path):
        return "Arquivo não encontrado", 404

    try:
        audio = AudioSegment.from_file(path)
        trecho = audio[inicio * 1000:fim * 1000]

        buffer = io.BytesIO()
        trecho.export(buffer, format="mp3")
        buffer.seek(0)

        nome_saida = f"recorte_{os.path.basename(path)}"
        return send_file(
            buffer,
            mimetype="audio/mpeg",
            as_attachment=True,
            download_name=nome_saida
        )

    except Exception as e:
        print(f"❌ Erro ao recortar: {e}")
        return "Erro ao processar o áudio", 500
