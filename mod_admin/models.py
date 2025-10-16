import sqlite3
from datetime import datetime
import os

# Caminho absoluto do banco local (usuarios.db)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, '..', 'usuarios.db')
DB_PATH = os.path.normpath(DB_PATH)


def get_connection():
    """Retorna uma conexão SQLite com autocommit habilitado."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


# ===========================================================
# 🔹 LOGINS
# ===========================================================

def registrar_login(usuario: str, tipo_login: str, ip: str = None):
    """Registra um login bem-sucedido no banco."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            tipo_login TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            ip TEXT
        )
    """)
    cur.execute("""
        INSERT INTO logins (usuario, tipo_login, data_hora, ip)
        VALUES (?, ?, ?, ?)
    """, (usuario, tipo_login, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), ip))
    conn.commit()
    conn.close()


def listar_logins(limit=100):
    """Retorna os últimos logins registrados."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT usuario, tipo_login, data_hora, ip
        FROM logins
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    registros = cur.fetchall()
    conn.close()
    return registros


def contar_logins():
    """Conta logins locais e LDAP."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM logins WHERE tipo_login='local'")
    total_local = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM logins WHERE tipo_login='ldap'")
    total_ldap = cur.fetchone()[0]

    conn.close()
    return {"local": total_local, "ldap": total_ldap}


# ===========================================================
# 🔹 USUÁRIOS
# ===========================================================

def listar_usuarios():
    """Retorna todos os usuários locais cadastrados no banco."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha TEXT,
            tipo TEXT
        )
    """)
    cur.execute("SELECT id, nome, usuario, tipo FROM usuarios ORDER BY id ASC")
    usuarios = cur.fetchall()
    conn.close()
    return usuarios


def contar_usuarios():
    """Retorna o total de usuários locais cadastrados."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM usuarios")
    total = cur.fetchone()[0]
    conn.close()
    return total


def inicializar_tabelas():
    """Garante que as tabelas necessárias existam no banco."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            usuario TEXT UNIQUE,
            senha TEXT,
            tipo TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS logins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL,
            tipo_login TEXT NOT NULL,
            data_hora TEXT NOT NULL,
            ip TEXT
        )
    """)
    conn.commit()
    conn.close()


# ===========================================================
# 🔹 CRUD DE USUÁRIOS LOCAIS
# ===========================================================

def obter_usuario_por_id(user_id):
    """Retorna os dados de um usuário específico pelo ID."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, nome, usuario, tipo FROM usuarios WHERE id = ?", (user_id,))
    user = cur.fetchone()
    conn.close()
    return user


def criar_usuario(nome, usuario, senha_hash, tipo):
    """Cria um novo usuário local."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO usuarios (nome, usuario, senha, tipo)
        VALUES (?, ?, ?, ?)
    """, (nome, usuario, senha_hash, tipo))
    conn.commit()
    conn.close()


def atualizar_usuario(user_id, nome, usuario, tipo):
    """Atualiza informações básicas de um usuário."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE usuarios
        SET nome = ?, usuario = ?, tipo = ?
        WHERE id = ?
    """, (nome, usuario, tipo, user_id))
    conn.commit()
    conn.close()


def excluir_usuario(user_id):
    """Remove um usuário local."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
