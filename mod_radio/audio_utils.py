from datetime import datetime, time
import os

def listar_audios(radio_config, data=None, hora_ini=None, hora_fim=None):
    """
    Lista arquivos de áudio usando a DATA/HORA DE CRIAÇÃO (ctime),
    com filtro opcional por data e janela de horário.
    Varre subpastas.
    Exibe logs de diagnóstico no console para facilitar debug.
    """
    pasta_base = radio_config["pasta_base"]
    extensao   = radio_config["extensao"]

    print(f"\n🎧 [CACHE] Iniciando varredura em: {pasta_base}")

    # normaliza hora_ini / hora_fim (podem vir como "" na querystring)
    def _parse_hhmm(v, default):
        if not v:
            return default
        try:
            return datetime.strptime(v, "%H:%M").time()
        except ValueError:
            return default

    h_ini = _parse_hhmm(hora_ini, time(0, 0, 0))
    h_fim = _parse_hhmm(hora_fim, time(23, 59, 59))

    audios = []

    # ⚠️ Verificação inicial da pasta
    if not os.path.exists(pasta_base):
        print(f"⚠️ [CACHE] Caminho inexistente: {pasta_base}")
        return audios

    try:
        for root, _, files in os.walk(pasta_base):
            for nome in files:
                if not nome.lower().endswith(extensao):
                    continue

                caminho = os.path.join(root, nome)
                try:
                    ctime_dt = datetime.fromtimestamp(os.path.getctime(caminho))  # data de CRIAÇÃO
                except Exception as e:
                    print(f"❌ [CACHE] Erro ao obter ctime de {caminho}: {e}")
                    continue

                # filtro por data (se fornecida)
                if data and ctime_dt.date() != data:
                    continue

                # filtro por janela de horário
                if not (h_ini <= ctime_dt.time() <= h_fim):
                    continue

                try:
                    tamanho_kb = os.path.getsize(caminho) / 1024
                except Exception as e:
                    print(f"🚫 [CACHE] Erro ao obter tamanho de {caminho}: {e}")
                    tamanho_kb = 0

                audios.append({
                    "nome": nome,
                    "datahora": ctime_dt.strftime("%d/%m/%Y %H:%M:%S"),
                    "tamanho": f"{tamanho_kb:,.0f} KB",
                    "caminho": caminho,
                    "_ts": ctime_dt.timestamp(),  # para ordenar com precisão
                })

        # ordena do mais novo para o mais antigo
        audios.sort(key=lambda x: x["_ts"], reverse=True)
        for a in audios:
            a.pop("_ts", None)

        print(f"✅ [CACHE] {len(audios)} arquivos encontrados em {pasta_base}")
        return audios

    except PermissionError:
        print(f"🚫 [CACHE] Permissão negada para acessar {pasta_base}")
        return []
    except Exception as e:
        print(f"💥 [CACHE] Erro inesperado ao listar {pasta_base}: {e}")
        return []
