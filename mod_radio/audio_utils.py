import os
from datetime import datetime, date, time

def listar_audios(radio_cfg, data=None, hora_ini=None, hora_fim=None):
    """
    Lista arquivos de áudio da rádio (com filtro de data/hora e paginação).
    - Busca em subpastas
    - Usa modificação do arquivo (mtime) como referência
    """
    pasta_base = radio_cfg["pasta_base"]
    extensao = radio_cfg["extensao"]

    audios = []

    # Se não existir, retorna vazio
    if not os.path.exists(pasta_base):
        return audios

    # Se foram enviados filtros de hora, converte para datetime.time
    hora_ini = datetime.strptime(hora_ini, "%H:%M").time() if hora_ini else time(0, 0)
    hora_fim = datetime.strptime(hora_fim, "%H:%M").time() if hora_fim else time(23, 59)

    # 🔍 Varre todas as subpastas
    for root, _, files in os.walk(pasta_base):
        for nome in files:
            if not nome.lower().endswith(extensao):
                continue

            caminho = os.path.join(root, nome)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(caminho))
            except FileNotFoundError:
                continue  # arquivo foi removido durante o scan

            # 🎯 Filtra por data/hora, se fornecido
            if data and mtime.date() != data:
                continue
            if not (hora_ini <= mtime.time() <= hora_fim):
                continue

            audios.append({
                "nome": nome,
                "pasta": os.path.relpath(root, pasta_base),
                "datahora": mtime.strftime("%d/%m/%Y %H:%M:%S"),
                "caminho": caminho
            })

    # Ordena do mais recente para o mais antigo
    audios.sort(key=lambda x: x["datahora"], reverse=True)
    return audios
