import os
import platform

# Detecta sistema operacional
SISTEMA = platform.system().lower()  # "windows" ou "linux"

# Define caminhos conforme sistema
if "windows" in SISTEMA:
    # 🪟 Caminhos de rede mapeados no Windows
    PASTA_CLUBE = r"\\10.14.0.42\clube fm"     # exemplo se estiver mapeado como Z:
    PASTA_MASSA = r"\\10.14.0.42\massa fm"     # ou altere conforme seu mapeamento
else:
    # 🐧 Caminhos montados no Linux
    PASTA_CLUBE = "/mnt/clube_fm"
    PASTA_MASSA = "/mnt/massa_fm"

# Configurações de rádios
RADIOS_CONFIG = {
    "clube": {
        "nome": "Rádio Clube Lages",
        "pasta_base": PASTA_CLUBE,
        "extensao": ".mp3",
        "estrutura": "diaria",
        "parse_nome": "clube",
    },
    "massa": {
        "nome": "Rádio Massa Lages",
        "pasta_base": PASTA_MASSA,
        "extensao": ".wav",
        "estrutura": "mensal",
        "parse_nome": "massa",
    },
}

# Configurações globais do Flask
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY = "chave-super-secreta"
DEBUG = True
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

# Log para verificação (opcional)
print(f"Sistema detectado: {SISTEMA}")
print(f"→ Clube FM: {PASTA_CLUBE}")
print(f"→ Massa FM: {PASTA_MASSA}")
