import os
import re
from datetime import datetime


# -------------------------------------------------------------------------
# 🔍 FUNÇÃO PRINCIPAL: LISTAR ÁUDIOS
# -------------------------------------------------------------------------
def listar_audios(radio_cfg, data=None, hora_ini=None, hora_fim=None):
    """
    Lista os áudios disponíveis na pasta configurada da rádio,
    aplicando filtros opcionais de data e hora.

    - radio_cfg: dict contendo as chaves "pasta_base" e "extensao"
    - data: str no formato YYYY-MM-DD
    - hora_ini, hora_fim: str no formato HH:MM
    """
    pasta_base = radio_cfg.get("pasta_base")
    extensao = radio_cfg.get("extensao", ".mp3").lower().strip(".")
    nome_radio = radio_cfg.get("nome", radio_cfg.get("chave", "?"))

    if not pasta_base or not os.path.exists(pasta_base):
        print(f"⚠️ [CACHE] Caminho inexistente: {pasta_base}")
        return []

    print(f"\n🎧 [CACHE] Iniciando varredura recursiva em: {pasta_base}")
    print(f"🎧 [CACHE] Extensões válidas para {nome_radio}: ['{extensao}']")

    audios = []

    for root, _, files in os.walk(pasta_base):
        for nome_arquivo in sorted(files):
            if not nome_arquivo.lower().endswith(f".{extensao}"):
                continue

            caminho = os.path.join(root, nome_arquivo)
            datahora = None

            # -----------------------------------------------------------------
            # 🧠 Tenta deduzir a data/hora
            # -----------------------------------------------------------------
            try:
                nome_limpo = os.path.splitext(nome_arquivo)[0]

                # 1️⃣ Caso principal: 14 dígitos consecutivos (YYYYMMDDHHMMSS)
                m = re.search(r"(\d{14})", nome_limpo)
                if m:
                    datahora = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
                    origem_data = "nome do arquivo (14 dígitos)"
                else:
                    # 2️⃣ Caso secundário: pasta DD-MM-YYYY
                    partes = os.path.normpath(caminho).split(os.sep)
                    pasta_data = next((p for p in partes if re.match(r"\d{2}-\d{2}-\d{4}$", p)), None)
                    if pasta_data:
                        datahora = datetime.strptime(pasta_data, "%d-%m-%Y")
                        origem_data = "pasta DD-MM-YYYY"
                    else:
                        # 3️⃣ Fallback: data do arquivo
                        datahora = datetime.fromtimestamp(os.path.getmtime(caminho))
                        origem_data = "mtime"
            except Exception as e:
                datahora = datetime.fromtimestamp(os.path.getmtime(caminho))
                origem_data = f"mtime (erro: {e})"

            # -----------------------------------------------------------------
            # 📅 FILTRO POR DATA
            # -----------------------------------------------------------------
            if data:
                try:
                    data_filtro = datetime.strptime(data, "%Y-%m-%d").date()
                    if datahora.date() != data_filtro:
                        continue
                except Exception:
                    pass

            # -----------------------------------------------------------------
            # ⏰ FILTRO POR HORÁRIO
            # -----------------------------------------------------------------
            if hora_ini or hora_fim:
                try:
                    h_ini = datetime.strptime(hora_ini or "00:00", "%H:%M").time()
                    h_fim = datetime.strptime(hora_fim or "23:59", "%H:%M").time()
                    if not (h_ini <= datahora.time() <= h_fim):
                        continue
                except Exception:
                    pass

            # -----------------------------------------------------------------
            # 📦 Adiciona ao resultado
            # -----------------------------------------------------------------
            tamanho_kb = round(os.path.getsize(caminho) / 1024, 2)
            audios.append({
                "nome": nome_arquivo,
                "datahora": datahora.strftime("%d/%m/%Y %H:%M:%S"),
                "tamanho": tamanho_kb,
                "path": caminho,
            })

    print(f"✅ [CACHE] {len(audios)} arquivos encontrados após filtros em {pasta_base}")
    return sorted(audios, key=lambda x: x["datahora"], reverse=True)


# -------------------------------------------------------------------------
# 🧩 UTILITÁRIO PARA DEBUG
# -------------------------------------------------------------------------
if __name__ == "__main__":
    exemplo = {
        "nome": "Radio Gralha",
        "pasta_base": r"C:\SCC\RadioAppOpec\media_drive\Radio_Gralha",
        "extensao": ".mp3"
    }
    arquivos = listar_audios(exemplo, data="2025-10-21", hora_ini="07:00", hora_fim="09:00")
    print("\nExemplo de saída:")
    for a in arquivos[:5]:
        print(a)
