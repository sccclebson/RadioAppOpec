import os
import io
from flask import Blueprint, make_response, render_template, session, redirect, url_for, send_file, request
from config import RADIOS
from .audio_utils import listar_audios
from datetime import datetime
from urllib.parse import quote, unquote
from pydub import AudioSegment
from datetime import datetime

from mod_auth.utils import login_required

bp_radio = Blueprint('radio', __name__, template_folder='templates')

def require_login(role=None):
    user = session.get('user')
    if not user:
        return redirect(url_for('auth.login'))
    if role and user['tipo'] != role:
        return "Acesso negado", 403

# 🔹 Selecionar a rádio
@bp_radio.route('/radio/select')
def select_radio():
    """Exibe lista de rádios disponíveis"""
    return render_template('select_radio.html', radios=RADIOS)


# 🔹 Salvar rádio escolhida
@bp_radio.route('/radio/<radio_id>')
def selecionar_radio(radio_id):
    """Salva rádio escolhida na sessão e redireciona para listagem"""
    if radio_id not in RADIOS:
        return "Rádio inválida", 404

    session['radio_selecionada'] = radio_id
    return redirect(url_for('radio.lista_audios'))


# 🔹 Página principal com o layout e scripts
@bp_radio.route('/radio/audios', methods=['GET'])
def lista_audios():
    check = require_login()
    if check: return check  # redireciona se não logado
    """Página de listagem de áudios (carrega interface, dados via AJAX)"""
    radio_id = session.get('radio_selecionada')
    if not radio_id:
        return redirect(url_for('radio.select_radio'))

    radio = RADIOS[radio_id]

    # Passa a data atual para o template
    data_hoje = datetime.now().strftime('%Y-%m-%d')

    return render_template('lista_audios.html', radio=radio, data_hoje=data_hoje)


# 🔹 Endpoint AJAX que envia apenas os dados (JSON)
@bp_radio.route('/radio/audios/data', methods=['GET'])
def lista_audios_data():
    """Retorna os áudios em formato JSON para a tabela via AJAX"""
    radio_id = session.get('radio_selecionada')
    if not radio_id:
        return {"error": "Rádio não selecionada"}, 400

    radio = RADIOS[radio_id]

    # Parâmetros
    data_str = request.args.get('data')
    hora_ini_str = request.args.get('hora_ini')
    hora_fim_str = request.args.get('hora_fim')
    page = int(request.args.get('page', 1))
    por_pagina = 10

    # Conversão
    data_filtro = datetime.strptime(data_str, '%Y-%m-%d') if data_str else datetime.now()
    hora_inicio = datetime.strptime(hora_ini_str, '%H:%M').time() if hora_ini_str else None
    hora_fim = datetime.strptime(hora_fim_str, '%H:%M').time() if hora_fim_str else None

    # Busca
    audios = listar_audios(radio, data_filtro)

    # Filtro por hora
    if hora_inicio or hora_fim:
        audios_filtrados = []
        for a in audios:
            try:
                hora_arquivo = datetime.strptime(a['datahora'], "%d/%m/%Y %H:%M:%S").time()
                if hora_inicio and hora_arquivo < hora_inicio:
                    continue
                if hora_fim and hora_arquivo > hora_fim:
                    continue
                audios_filtrados.append(a)
            except Exception:
                audios_filtrados.append(a)
        audios = audios_filtrados

    # Paginação
    total = len(audios)
    total_paginas = (total + por_pagina - 1) // por_pagina
    inicio = (page - 1) * por_pagina
    fim = inicio + por_pagina
    audios_pagina = audios[inicio:fim]

    return {
        "audios": audios_pagina,
        "pagina_atual": page,
        "total_paginas": total_paginas,
    }


# 🔹 Servir o áudio diretamente para o Wavesurfer
@bp_radio.route('/radio/play')
def play_audio():
    """Envia o arquivo de áudio para o player (Wavesurfer)"""
    caminho = request.args.get('path')
    if not caminho:
        return "Caminho ausente", 400

    caminho = unquote(caminho).replace('/', os.sep)
    print(f"[DEBUG] Solicitando áudio: {caminho}")

    if not os.path.exists(caminho):
        print(f"[ERRO] Caminho não encontrado: {caminho}")
        return "Arquivo não encontrado", 404

    ext = os.path.splitext(caminho)[1].lower()
    mimetype = "audio/mpeg" if ext == ".mp3" else "audio/wav"

    # 🔹 Retornar o arquivo desativando cache
    response = make_response(send_file(caminho, mimetype=mimetype))
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    return response


# 🔹 Página de recorte
@bp_radio.route('/radio/recortar')
def recortar_audio():
    """Página para recorte de áudio"""
    path = request.args.get('path')

    if not path or not os.path.exists(path):
        return "Arquivo não encontrado", 404

    nome_arquivo = os.path.basename(path)
    return render_template(
        'recortar_audio.html',
        path=path,  # mantém o caminho cru, o HTML faz o encode
        nome_arquivo=nome_arquivo
    )


# 🔹 Gerar e baixar recorte
@bp_radio.route('/radio/recortar/download', methods=['POST'])
def recortar_download():
    """Gera o recorte e envia o arquivo"""
    path = request.form.get('path')
    tempo_inicio = float(request.form.get('inicio', 0))
    tempo_fim = float(request.form.get('fim', 0))

    if not path:
        return "Caminho ausente", 400

    path = unquote(path)
    if not os.path.exists(path):
        return f"Arquivo não encontrado: {path}", 404

    # 🔹 Recorte com Pydub
    audio = AudioSegment.from_file(path)
    recorte = audio[tempo_inicio * 1000:tempo_fim * 1000]

    buffer = io.BytesIO()
    recorte.export(buffer, format="mp3")
    buffer.seek(0)

    nome_saida = os.path.basename(path).replace(".mp3", "_recorte.mp3")

    return send_file(
        buffer,
        as_attachment=True,
        download_name=nome_saida,
        mimetype="audio/mpeg"
    )
