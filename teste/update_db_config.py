import sqlite3

sql_commands = """
CREATE TABLE IF NOT EXISTS tb_config_ldap (
  id_config_ldap INTEGER PRIMARY KEY AUTOINCREMENT,
  servidor TEXT NOT NULL,
  porta INTEGER NOT NULL DEFAULT 389,
  dominio TEXT NOT NULL,
  usuario_base TEXT NOT NULL,
  usuario_bind TEXT,
  senha_bind TEXT,
  usar_ssl INTEGER NOT NULL DEFAULT 0,
  timeout INTEGER NOT NULL DEFAULT 5,
  status TEXT NOT NULL DEFAULT 'ativo',
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tb_radios (
  id_radio INTEGER PRIMARY KEY AUTOINCREMENT,
  chave TEXT NOT NULL UNIQUE,
  nome TEXT NOT NULL,
  pasta_base TEXT NOT NULL,
  extensao TEXT NOT NULL DEFAULT '.mp3',
  parse_nome TEXT,
  ativa INTEGER NOT NULL DEFAULT 1,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tb_config_sistema (
  id INTEGER PRIMARY KEY CHECK (id = 1),
  secret_key TEXT,
  cache_intervalo_min INTEGER NOT NULL DEFAULT 10,
  max_por_pagina INTEGER NOT NULL DEFAULT 20
);

INSERT OR IGNORE INTO tb_config_sistema (id, secret_key, cache_intervalo_min, max_por_pagina)
VALUES (1, NULL, 10, 20);
"""

# Caminho para o banco de dados
db_path = "usuarios.db"

conn = sqlite3.connect(db_path)
conn.executescript(sql_commands)
conn.commit()
conn.close()

print("✅ Tabelas de configuração criadas/atualizadas com sucesso!")
