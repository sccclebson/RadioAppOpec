# mod_radio/audio_cache.py
import os
import json
from datetime import datetime
from pathlib import Path
from mod_radio.audio_utils import listar_audios
from mod_config.models import carregar_radios_config

# Caminho do cache local
CACHE_PATH = os.path.join(os.getcwd(), "cache_local.json")

# Estruturas em memória
CACHE_AUDIOS = {}
CACHE_TIMESTAMP = {}
CACHE_INTERVALO_MINUTOS = 10  # intervalo padrão


# -------------------------------------------------------------------------
# FUNÇÕES AUXILIARES
# -------------------------------------------------------------------------
def carregar_cache():
    """Carrega cache do arquivo JSON para memória."""
    global CACHE_AUDIOS, CACHE_TIMESTAMP
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                CACHE_AUDIOS = data.get("audios", {})
                CACHE_TIMESTAMP = data.get("timestamp", {})
            print(f"📦 Cache local carregado: {len(CACHE_AUDIOS)} rádios.")
        except Exception as e:
            print("⚠️ Erro ao carregar cache local:", e)
    else:
        print("ℹ️ Nenhum cache local encontrado.")


def salvar_cache():
    """Salva o cache em disco."""
    try:
        data = {"audios": CACHE_AUDIOS, "timestamp": CACHE_TIMESTAMP}
        with open(CACHE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("💾 Cache salvo com sucesso.")
    except Exception as e:
        print("⚠️ Erro ao salvar cache:", e)


# -------------------------------------------------------------------------
# CACHE PRINCIPAL
# -------------------------------------------------------------------------
def atualizar_cache(radio_key, radio_cfg=None):
    """Atualiza o cache local da rádio (Drive sincronizado ou local)."""
    from mod_config.models import carregar_radios_config

    if not radio_cfg:
        radios_cfg = carregar_radios_config()
        radio_cfg = radios_cfg.get(radio_key)

    if not radio_cfg:
        print(f"⚠️ [CACHE] Rádio '{radio_key}' não encontrada nas configurações.")
        return

    base_dir = radio_cfg.get("pasta_base") or ""
    tipo = radio_cfg.get("tipo_pasta") or "local"
    extensao = radio_cfg.get("extensao", ".mp3")

    print(f"💾 [CACHE] Rádio '{radio_key}' → tipo: {tipo}, extensões: {extensao}")
    print(f"💾 [CACHE] Pasta configurada: {base_dir}")

    # -----------------------------------------------------------------
    # 🧠 Detecta se é uma rádio vinculada ao Google Drive
    # -----------------------------------------------------------------
    if tipo == "drive" or "[Google Drive]" in base_dir:
        MEDIA_DIR = Path(os.getcwd()) / "media_drive"

        possiveis = [
            MEDIA_DIR / radio_key,
            MEDIA_DIR / radio_cfg.get("nome", "").strip().replace(" ", "_"),
            MEDIA_DIR / base_dir.replace("[Google Drive]", "").strip().replace(" ", "_"),
        ]

        sync_path = None
        for p in possiveis:
            if p.exists():
                sync_path = p
                break

        if not sync_path:
            print(f"⚠️ [CACHE] Nenhuma pasta sincronizada encontrada para '{radio_key}' em {MEDIA_DIR}")
            CACHE_AUDIOS[radio_key] = []
            return

        base_dir = str(sync_path)
        print(f"💾 [CACHE] Usando pasta sincronizada local: {base_dir}")

    # -----------------------------------------------------------------
    # 🔎 Varre os arquivos e atualiza o cache
    # -----------------------------------------------------------------
    if not os.path.exists(base_dir):
        print(f"⚠️ [CACHE] Caminho inexistente: {base_dir}")
        CACHE_AUDIOS[radio_key] = []
        return

    print(f"🎧 [CACHE] Iniciando varredura recursiva em: {base_dir}")
    radio_cfg_local = {
        "pasta_base": base_dir,
        "extensao": extensao,
        "chave": radio_key,
        "nome": radio_cfg.get("nome", radio_key)
    }

    audios = listar_audios(radio_cfg_local)
    CACHE_AUDIOS[radio_key] = audios
    CACHE_TIMESTAMP[radio_key] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    salvar_cache()
    print(f"✅ [CACHE] Cache atualizado para '{radio_key}' ({len(audios)} arquivos).")


def obter_cache(radio_key):
    """Obtém os áudios do cache em memória."""
    return CACHE_AUDIOS.get(radio_key, [])


# -------------------------------------------------------------------------
# INICIALIZAÇÃO AUTOMÁTICA
# -------------------------------------------------------------------------
def inicializar_cache_local():
    """Carrega cache local na inicialização."""
    print("🧩 Inicializando sistema de cache local...")
    carregar_cache()
    print("✅ Cache local pronto.")
