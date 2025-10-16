import sqlite3
import os

# Garante que todos os módulos usem o mesmo banco
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, '..', 'usuarios.db'))

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def criar_tabela_usuarios():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                usuario TEXT UNIQUE NOT NULL,
                senha TEXT NOT NULL,
                tipo TEXT NOT NULL
            )
        """)
        conn.commit()

def salvar_usuario(user):
    criar_tabela_usuarios()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO usuarios (nome, usuario, senha, tipo) VALUES (?, ?, ?, ?)",
            (user['nome'], user['usuario'], user['senha'], user['tipo'])
        )
        conn.commit()

def buscar_usuario(usuario):
    criar_tabela_usuarios()
    with get_connection() as conn:
        cur = conn.execute("SELECT * FROM usuarios WHERE usuario = ?", (usuario,))
        return cur.fetchone()
