# mod_radio/audio_cache.py
import threading
import time
from datetime import datetime
from mod_radio.audio_utils import listar_audios
from config import RADIOS_CONFIG

# Cache em memória
CACHE_AUDIOS = {}
CACHE_TIMESTAMP = {}
CACHE_INTERVALO_MINUTOS = 10  # tempo de atualização automática

def atualizar_cache(radio_key):
    """Atualiza o cache de uma rádio específica."""
    radio_cfg = RADIOS_CONFIG.get(radio_key)
    if not radio_cfg:
        return

    try:
        print(f"🔄 Atualizando cache de {radio_cfg['nome']}...")
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
