import os
import platform

# Detecta sistema operacional
SISTEMA = platform.system().lower()  # windows, linux, darwin (macOS)

# Função auxiliar: retorna o primeiro caminho que existir
def primeiro_caminho_valido(caminhos):
    for caminho in caminhos:
        if os.path.exists(caminho):
            return caminho
    return None

# 🪟 Configuração para Windows (mapas e compartilhamentos de rede)
if "windows" in SISTEMA:
    PASTA_CLUBE = primeiro_caminho_valido([
        r"C:\PROJETOS\Radios\Clube"
    ])
    PASTA_MASSA = primeiro_caminho_valido([
        r"C:\PROJETOS\Radios\Massa"
    ])

# 🐧 Configuração para Linux (montagens locais)
else:
    PASTA_CLUBE = primeiro_caminho_valido([
        "/mnt/clube_fm",
        "/media/clube_fm"
    ])
    PASTA_MASSA = primeiro_caminho_valido([
        "/mnt/massa_fm",
        "/media/massa_fm"
    ])

# Configurações das rádios
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

# Log informativo
print(f"\n🧩 Sistema detectado: {SISTEMA}")
print(f"📂 Clube FM → {PASTA_CLUBE}")
print(f"📂 Massa FM → {PASTA_MASSA}\n")
