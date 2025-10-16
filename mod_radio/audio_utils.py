from datetime import datetime
import os

def parser_clube(nome_arquivo):
    """
    Exemplo: 20251014000749.mp3 → 2025/10/14 00:07:49
    """
    base = os.path.splitext(nome_arquivo)[0]  # remove extensão
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
        hora = hora.zfill(4)  # garante 4 dígitos (ex: 0120)
        hora_formatada = f"{hora[:2]}:{hora[2:]}"
        return {"dia": dia, "hora": hora_formatada}
    except Exception:
        return None


def listar_audios(radio_config, data=None):
    """
    Lista os arquivos de áudio de uma rádio conforme a configuração.
    """
    caminho_base = radio_config["pasta_base"]
    extensao = radio_config["extensao"]
    estrutura = radio_config["estrutura"]
    parser = radio_config["parse_nome"]

    audios = []

    # Montar caminho conforme tipo de estrutura
    if estrutura == "diaria":
        # Rádio Clube → subpasta do dia ex: 11-10-2025
        if data:
            subpasta = data.strftime("%d-%m-%Y")
        else:
            subpasta = datetime.now().strftime("%d-%m-%Y")
        pasta_dia = os.path.join(caminho_base, subpasta)
    else:
        # Rádio Massa → subpasta do mês ex: agosto
        if data:
            subpasta = data.strftime("%B").lower()  # nome do mês
        else:
            subpasta = datetime.now().strftime("%B").lower()
        pasta_dia = os.path.join(caminho_base, subpasta)

    if not os.path.exists(pasta_dia):
        return []

    for arquivo in os.listdir(pasta_dia):
        if arquivo.endswith(extensao):
            caminho = os.path.join(pasta_dia, arquivo)
            tamanho_kb = os.path.getsize(caminho) / 1024

            if parser == "clube":
                datahora = parser_clube(arquivo)
                datahora_str = datahora.strftime("%d/%m/%Y %H:%M:%S") if datahora else "?"
            else:
                info = parser_massa(arquivo)
                datahora_str = f"{info['dia']} {info['hora']}" if info else "?"

            audios.append({
                "nome": arquivo,
                "datahora": datahora_str,
                "tamanho": f"{tamanho_kb:,.0f} KB",
                "caminho": caminho
            })

    return sorted(audios, key=lambda x: x["nome"], reverse=True)
