import os
import json
import time
from datetime import datetime
from mod_config.models import carregar_radios_config, ConfigGoogleDrive
from mod_config.google_drive_utils import build_drive_service
from .audio_utils import listar_audios

# Cache em memória
CACHE_LOCAL = {}
CACHE_DRIVE = {}

# Caminho do arquivo de cache persistente para rádios do Drive
CACHE_DRIVE_FILE = os.path.join(os.path.dirname(__file__), "cache_drive.json")


# -------------------------------------------------------------------------
# Funções auxiliares
# -------------------------------------------------------------------------
def salvar_cache_drive():
    """Salva o cache do Drive no disco."""
    try:
        with open(CACHE_DRIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(CACHE_DRIVE, f, indent=2, ensure_ascii=False)
        print(f"💾 [CACHE] Arquivo salvo: {len(CACHE_DRIVE)} rádios no cache persistente.")
    except Exception as e:
        print(f"❌ [CACHE] Falha ao salvar cache_drive.json: {e}")


def carregar_cache_drive():
    """Carrega o cache persistente do Drive (se existir)."""
    global CACHE_DRIVE
    if os.path.exists(CACHE_DRIVE_FILE):
        try:
            with open(CACHE_DRIVE_FILE, "r", encoding="utf-8") as f:
                CACHE_DRIVE = json.load(f)
            print(f"☁️ [DRIVE] Cache persistente carregado: {len(CACHE_DRIVE)} rádios.")
        except Exception as e:
            print(f"⚠️ [DRIVE] Erro ao carregar cache persistente: {e}")
            CACHE_DRIVE = {}
    else:
        CACHE_DRIVE = {}


# -------------------------------------------------------------------------
# Funções principais
# -------------------------------------------------------------------------
def obter_cache(radio_key):
    """Obtém o cache (local ou Drive) da rádio."""
    radios_cfg = carregar_radios_config()
    radio = radios_cfg.get(radio_key)

    if not radio:
        print(f"⚠️ [CACHE] Rádio '{radio_key}' não encontrada.")
        return []

    # Rádio Drive
    if radio.get("tipo_pasta") == "drive" or "[Google Drive]" in (radio.get("pasta_base") or ""):
        cache = CACHE_DRIVE.get(radio_key, [])
        print(f"☁️ [DRIVE] Cache carregado para '{radio_key}' ({len(cache)} arquivos).")
        return cache

    # Rádio local
    cache = CACHE_LOCAL.get(radio_key, [])
    print(f"🎧 [LOCAL] Cache carregado para '{radio_key}' ({len(cache)} arquivos).")
    return cache


def atualizar_cache(radio_key=None):
    """Atualiza o cache (local ou Drive) para uma rádio específica ou todas."""
    radios_cfg = carregar_radios_config()

    if radio_key:
        radios = {radio_key: radios_cfg.get(radio_key)}
    else:
        radios = radios_cfg

    for key, radio in radios.items():
        if not radio:
            continue

        # Rádio Drive ------------------------------------------------------
        if radio.get("tipo_pasta") == "drive" or "[Google Drive]" in (radio.get("pasta_base") or ""):
            try:
                print(f"🔄 [DRIVE] Atualizando cache para '{key}'...")

                cfg_drive = ConfigGoogleDrive.get()
                if not cfg_drive:
                    print("⚠️ [DRIVE] Configuração do Google Drive não encontrada.")
                    continue

                service = build_drive_service(cfg_drive)

                # Buscar folder_id no banco
                import sqlite3
                from pathlib import Path
                db_path = Path(__file__).resolve().parents[1] / "usuarios.db"
                conn = sqlite3.connect(db_path)
                conn.row_factory = sqlite3.Row
                row = conn.execute(
                    "SELECT drive_folder_id FROM tb_radios WHERE chave=?",
                    (key,)
                ).fetchone()
                conn.close()

                folder_id = row["drive_folder_id"] if row else None
                if not folder_id:
                    print(f"⚠️ [DRIVE] Pasta do Drive não configurada para '{key}'.")
                    continue

                # Busca recursiva no Drive
                def listar_drive_recursivo(folder_id, extensoes=(".mp3", ".wav")):
                    encontrados = []
                    query = f"'{folder_id}' in parents and trashed=false"
                    results = service.files().list(
                        q=query,
                        fields="files(id, name, mimeType, size, modifiedTime)",
                        orderBy="modifiedTime desc"
                    ).execute()

                    for f in results.get("files", []):
                        mime = f.get("mimeType", "")
                        nome = f.get("name", "")
                        if mime == "application/vnd.google-apps.folder":
                            encontrados.extend(listar_drive_recursivo(f["id"], extensoes))
                        elif nome.lower().endswith(extensoes):
                            encontrados.append(f)
                    return encontrados

                files = listar_drive_recursivo(folder_id)

                audios = []
                for f in files:
                    nome = f.get("name")
                    modificado = f.get("modifiedTime")
                    tamanho = int(f.get("size", 0)) / 1024 if f.get("size") else 0
                    audios.append({
                        "nome": nome,
                        "datahora": datetime.strptime(modificado, "%Y-%m-%dT%H:%M:%S.%fZ").strftime("%d/%m/%Y %H:%M:%S"),
                        "tamanho": f"{tamanho:,.0f} KB",
                        "caminho": f"https://drive.google.com/uc?id={f['id']}&export=download"
                    })

                CACHE_DRIVE[key] = audios
                salvar_cache_drive()
                print(f"✅ [DRIVE] Cache atualizado para '{key}' ({len(audios)} arquivos).")

            except Exception as e:
                print(f"❌ [DRIVE] Erro ao atualizar cache para '{key}': {e}")

        # Rádio local ------------------------------------------------------
        else:
            try:
                print(f"🔄 [LOCAL] Atualizando cache para '{key}'...")
                audios = listar_audios(radio)
                CACHE_LOCAL[key] = audios
                print(f"✅ [LOCAL] Cache atualizado para '{key}' ({len(audios)} arquivos).")
            except Exception as e:
                print(f"❌ [LOCAL] Erro ao atualizar cache para '{key}': {e}")

    print("💾 [CACHE] Atualização completa.")


# -------------------------------------------------------------------------
# Inicialização automática
# -------------------------------------------------------------------------
def inicializar_cache():
    """Carrega o cache persistente do Drive na inicialização do app."""
    print("🧩 Inicializando sistema de cache (local + Drive)...")
    carregar_cache_drive()
    print("✅ Sistema de cache pronto.")


# Executar carregamento automático ao importar
inicializar_cache()
