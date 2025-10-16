from datetime import datetime
import os

def listar_audios(radio_config, data=None, hora_ini=None, hora_fim=None):
    """
    Lista os arquivos de áudio usando a data/hora de criação real (ctime).
    Suporta filtragem por data e hora.
    """
    pasta_base = radio_config["pasta_base"]
    extensao = radio_config["extensao"]
    audios = []

    if not os.path.exists(pasta_base):
        return audios

    for root, _, files in os.walk(pasta_base):
        for nome in files:
            if not nome.lower().endswith(extensao):
                continue

            caminho = os.path.join(root, nome)
            try:
                # 🕒 Data/hora de criação real
                ctime = datetime.fromtimestamp(os.path.getctime(caminho))
            except Exception:
                continue

            # 🎯 Filtro por data
            if data and ctime.date() != data:
                continue

            # 🎯 Filtro por hora (opcional)
            if hora_ini:
                try:
                    h_ini = datetime.strptime(hora_ini, "%H:%M").time()
                    if ctime.time() < h_ini:
                        continue
                except ValueError:
                    pass
            if hora_fim:
                try:
                    h_fim = datetime.strptime(hora_fim, "%H:%M").time()
                    if ctime.time() > h_fim:
                        continue
                except ValueError:
                    pass

            tamanho_kb = os.path.getsize(caminho) / 1024
            audios.append({
                "nome": nome,
                "datahora": ctime.strftime("%d/%m/%Y %H:%M:%S"),
                "tamanho": f"{tamanho_kb:,.0f} KB",
                "caminho": caminho
            })

    # 🔄 Ordena pelos mais recentes
    return sorted(audios, key=lambda x: x["datahora"], reverse=True)
