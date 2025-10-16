# config.py
import os

BASE_PATH = r"C:\PROJETOS\Radios"

RADIOS = {
    "clube": {
        "nome": "Rádio Clube Lages",
        "pasta_base": os.path.join(BASE_PATH, "Clube"),
        "estrutura": "diaria",   # subpasta: 11-10-2025
        "extensao": ".mp3",
        "parse_nome": "clube",   # usa função parser_clube()
    },
    "massa": {
        "nome": "Rádio Massa Lages",
        "pasta_base": os.path.join(BASE_PATH, "Massa"),
        "estrutura": "mensal",   # subpasta: agosto/
        "extensao": ".wav",
        "parse_nome": "massa",   # usa função parser_massa()
    },
}
