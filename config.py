import os

# Caminhos de rede montados no Linux
RADIOS_CONFIG = {
    "clube": {
        "nome": "Rádio Clube Lages",
        "pasta_base": "/mnt/clube_fm",  # caminho montado da rede
        "extensao": ".mp3",
        "parse_nome": "clube",
    },
    "massa": {
        "nome": "Rádio Massa Lages",
        "pasta_base": "/mnt/massa_fm",  # caminho montado da rede
        "extensao": ".mp3",
        "parse_nome": "massa",
    },
}

# Configurações globais do Flask
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SECRET_KEY = "chave-super-secreta"
DEBUG = True
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
