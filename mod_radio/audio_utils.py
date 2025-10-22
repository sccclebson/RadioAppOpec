from pathlib import Path
from mod_config.models import get_media_drive_dir
import os
import re
from datetime import datetime


# -------------------------------------------------------------------------
# 🔍 FUNÇÃO PRINCIPAL: LISTAR ÁUDIOS
# -------------------------------------------------------------------------
def listar_audios(radio_cfg, data=None, hora_ini=None, hora_fim=None):
    pasta_base = radio_cfg.get("pasta_base")
    extensao = radio_cfg.get("extensao", ".mp3").lower()

    # 🔧 Correção automática de caminho simbólico (ex: "[Google Drive] Radio Clube")
    if pasta_base and not os.path.isabs(pasta_base):
        pasta_base = Path(get_media_drive_dir()) / pasta_base.replace("[Google Drive]", "").strip()

    if not pasta_base or not os.path.isdir(pasta_base):
        print(f"⚠️ [LISTAR] Pasta base inválida: {pasta_base}")
        return []

    audios = []

    for root, dirs, files in os.walk(pasta_base):
        for nome_arquivo in files:
            if not nome_arquivo.lower().endswith((".mp3", ".wav")):
                continue

            caminho = os.path.join(root, nome_arquivo)

            try:
                nome_limpo = os.path.splitext(nome_arquivo)[0]
                m = re.search(r"(\d{14})", nome_limpo)
                if m:
                    datahora = datetime.strptime(m.group(1), "%Y%m%d%H%M%S")
                else:
                    stat = os.stat(caminho)
                    datahora = datetime.fromtimestamp(stat.st_mtime)
            except Exception:
                stat = os.stat(caminho)
                datahora = datetime.fromtimestamp(stat.st_mtime)

            base_drive = get_media_drive_dir()
            subpath = Path(os.path.relpath(caminho, base_drive)).as_posix()
            tamanho_kb = round(os.path.getsize(caminho) / 1024, 2)

            audios.append({
                "nome": nome_arquivo,
                "datahora": datahora.strftime("%d/%m/%Y %H:%M:%S"),
                "tamanho": tamanho_kb,
                "subpath": subpath
            })

    print(f"✅ [CACHE] {len(audios)} arquivos encontrados em {pasta_base}")
    return sorted(audios, key=lambda x: x["datahora"], reverse=True)


# -------------------------------------------------------------------------
# 🧩 UTILITÁRIO PARA DEBUG (opcional)
# -------------------------------------------------------------------------
if __name__ == "__main__":
    from mod_config.models import carregar_radios_config
    radios = carregar_radios_config()
    radio = radios.get("clube")
    if radio:
        lista = listar_audios(radio)
        for a in lista[:5]:
            print(a)
