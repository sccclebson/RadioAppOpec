# mod_radio/audio_cache.py
import threading
import time
from datetime import datetime
from mod_config.models import carregar_radios_config
from mod_radio.audio_utils import listar_audios
from config import RADIOS_CONFIG

# Cache em memória
CACHE_AUDIOS = {}
CACHE_TIMESTAMP = {}
CACHE_INTERVALO_MINUTOS = 10  # tempo de atualização automática

def atualizar_cache(radio_key):
    """Atualiza o cache de uma rádio específica, com validação de caminho."""
    try:
        # Carrega a configuração atualizada das rádios
        radios_cfg = carregar_radios_config()
        radio_cfg = radios_cfg.get(radio_key)

        # Se não houver configuração ou pasta inválida, ignora
        if not radio_cfg or not radio_cfg.get("pasta_base"):
            print(f"⚠️ [CACHE] Rádio '{radio_key}' sem pasta_base definida. Ignorando atualização.")
            return

        print(f"🔄 Atualizando cache de {radio_cfg['nome']}...")

        # Lista e armazena os áudios
        CACHE_AUDIOS[radio_key] = listar_audios(radio_cfg)
        CACHE_TIMESTAMP[radio_key] = datetime.now()

        print(f"✅ Cache atualizado ({len(CACHE_AUDIOS[radio_key])} arquivos)")
    except Exception as e:
        print(f"❌ Erro ao atualizar cache da rádio {radio_key}: {e}")


def obter_cache(radio_key):
    """Retorna o cache da rádio, atualizando se necessário."""
    agora = datetime.now()
    ultima_atualizacao = CACHE_TIMESTAMP.get(radio_key)

    # Atualiza se o cache não existir ou estiver velho
    if not ultima_atualizacao or (agora - ultima_atualizacao).total_seconds() > CACHE_INTERVALO_MINUTOS * 60:
        atualizar_cache(radio_key)

    return CACHE_AUDIOS.get(radio_key, [])


def iniciar_cache_automatico(intervalo_minutos=10):
    """Inicia uma thread de atualização automática em segundo plano."""
    global CACHE_INTERVALO_MINUTOS
    CACHE_INTERVALO_MINUTOS = intervalo_minutos

    def worker():
        while True:
            for radio_key in RADIOS_CONFIG.keys():
                atualizar_cache(radio_key)
            time.sleep(intervalo_minutos * 60)

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    print(f"🕒 Atualização automática de cache iniciada ({intervalo_minutos}min)")
