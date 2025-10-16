from datetime import datetime
import os

def parser_clube(nome_arquivo):
    base = os.path.splitext(nome_arquivo)[0]
    try:
        return datetime.strptime(base, "%Y%m%d%H%M%S")
    except ValueError:
        return None


def parser_massa(nome_arquivo):
    base = os.path.splitext(nome_arquivo)[0]
    try:
        dia, hora = base.split("-")
        hora = hora.zfill(4)
        return {"dia": dia, "hora": f"{hora[:2]}:{hora[2:]}"}
    except Exception:
        return None


def listar_audios(radio_config, data=None):
    """
    Lista arquivos de áudio recursivamente.
    Suporta caminhos locais e de rede (UNC).
    """
    caminho_base = radio_config["pasta_base"]
    extensao = radio_config["extensao"]
    parser = radio_config["parse_nome"]

    audios = []

    # 🔍 Varre todas as subpastas
    for root, _, files in os.walk(caminho_base):
        for arquivo in files:
            if not arquivo.lower().endswith(extensao.lower()):
                continue

            caminho = os.path.join(root, arquivo)
            tamanho_kb = os.path.getsize(caminho) / 1024

            # Data/hora (tentativa de parse)
            if parser == "clube":
                datahora = parser_clube(arquivo)
                datahora_str = datahora.strftime("%d/%m/%Y %H:%M:%S") if datahora else "?"
            elif parser == "massa":
                info = parser_massa(arquivo)
                datahora_str = f"{info['dia']} {info['hora']}" if info else "?"
            else:
                # Se não tiver parser, usa a data do arquivo
                dt = datetime.fromtimestamp(os.path.getmtime(caminho))
                datahora_str = dt.strftime("%d/%m/%Y %H:%M:%S")

            audios.append({
                "nome": arquivo,
                "datahora": datahora_str,
                "tamanho": f"{tamanho_kb:,.0f} KB",
                "caminho": caminho.replace("\\", "/")
            })

    # Ordenar por data (ou nome)
    return sorted(audios, key=lambda x: x["datahora"], reverse=True)
