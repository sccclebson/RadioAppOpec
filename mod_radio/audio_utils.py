from datetime import datetime, time
import os
from pathlib import Path

def listar_audios(radio_config, data=None, hora_ini=None, hora_fim=None):
    """
    Lista arquivos de áudio com filtro opcional por data e hora.
    Compatível com pastas locais e sincronizadas do Google Drive.
    """
    pasta_base = radio_config.get("pasta_base", "")
    extensao   = radio_config.get("extensao", ".mp3")
    radio_key  = radio_config.get("chave") or radio_config.get("key") or ""

    # 🔄 Se for rádio sincronizada, tenta usar pasta real existente
    if pasta_base.startswith("[Google Drive]"):
        MEDIA_DIR = Path.cwd() / "media_drive"
        possiveis = [
            MEDIA_DIR / radio_key,
            MEDIA_DIR / radio_config.get("nome", "").strip().replace(" ", "_"),
            MEDIA_DIR / pasta_base.replace("[Google Drive]", "").strip().replace(" ", "_"),
        ]
        for p in possiveis:
            if p.exists():
                pasta_base = str(p)
                print(f"🔄 [AUDIO_UTILS] Usando pasta sincronizada local: {pasta_base}")
                break

    print(f"\n🎧 [CACHE] Iniciando varredura em: {pasta_base}")

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

    if not os.path.exists(pasta_base):
        print(f"⚠️ [CACHE] Caminho inexistente: {pasta_base}")
        return audios

    try:
        for root, _, files in os.walk(pasta_base):
            for nome in files:
                if not nome.lower().endswith(extensao.lower()):
                    continue

                caminho = os.path.join(root, nome)
                try:
                    ctime_dt = datetime.fromtimestamp(os.path.getctime(caminho))
                except Exception as e:
                    print(f"❌ [CACHE] Erro ao obter ctime de {caminho}: {e}")
                    continue

                if data and ctime_dt.date() != data:
                    continue

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
                    "_ts": ctime_dt.timestamp(),
                })

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
