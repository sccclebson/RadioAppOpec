from datetime import datetime
import os

def parser_clube(nome_arquivo):
    """
    Exemplo: 20251014000749.mp3 → 2025/10/14 00:07:49
    """
    base = os.path.splitext(nome_arquivo)[0]
    try:
        datahora = datetime.strptime(base, "%Y%m%d%H%M%S")
        return datahora
    except ValueError:
        return None


def parser_massa(nome_arquivo):
    """
    Exemplo: 01-0120.wav → dia=01, hora=01:20 (mês inferido pela pasta)
    """
    base = os.path.splitext(nome_arquivo)[0]
    try:
        dia, hora = base.split("-")
        hora = hora.zfill(4)
        hora_formatada = f"{hora[:2]}:{hora[2:]}"
        return {"dia": dia, "hora": hora_formatada}
    except Exception:
        return None


def listar_audios(radio_config, data=None):
    """
    Lista os arquivos de áudio usando a data/hora de CRIAÇÃO real (ctime).
    """
    caminho_base = radio_config["pasta_base"]
    extensao = radio_config["extensao"]
    estrutura = radio_config["estrutura"]
    parser = radio_config["parse_nome"]

    audios = []

    # Define subpasta (por dia ou mês)
    if estrutura == "diaria":
        subpasta = data.strftime("%d-%m-%Y") if data else datetime.now().strftime("%d-%m-%Y")
        pasta_dia = os.path.join(caminho_base, subpasta)
    else:
        subpasta = data.strftime("%B").lower() if data else datetime.now().strftime("%B").lower()
        pasta_dia = os.path.join(caminho_base, subpasta)

    if not os.path.exists(pasta_dia):
        return []

    for arquivo in os.listdir(pasta_dia):
        if not arquivo.lower().endswith(extensao):
            continue

        caminho = os.path.join(pasta_dia, arquivo)
        try:
            # ⚙️ Usa a data/hora de criação real
            datahora = datetime.fromtimestamp(os.path.getctime(caminho))
        except Exception:
            continue

        tamanho_kb = os.path.getsize(caminho) / 1024
        datahora_str = datahora.strftime("%d/%m/%Y %H:%M:%S")

        audios.append({
            "nome": arquivo,
            "datahora": datahora_str,
            "tamanho": f"{tamanho_kb:,.0f} KB",
            "caminho": caminho
        })

    # Ordena pelos mais recentes
    return sorted(audios, key=lambda x: x["datahora"], reverse=True)
