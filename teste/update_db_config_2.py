import sqlite3

sql_commands = """
-- 🔹 Criação da tabela de configuração do Google Drive
CREATE TABLE IF NOT EXISTS tb_config_drive (
  id_config INTEGER PRIMARY KEY AUTOINCREMENT,
  client_id TEXT NOT NULL,
  client_secret TEXT NOT NULL,
  access_token TEXT,
  refresh_token TEXT,
  token_expiry TEXT,
  user_email TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  updated_at TEXT DEFAULT (datetime('now'))
);

-- 🔹 Adição de novos campos em tb_radios, se ainda não existirem
ALTER TABLE tb_radios ADD COLUMN tipo_pasta TEXT DEFAULT 'local';
ALTER TABLE tb_radios ADD COLUMN drive_folder_id TEXT;
ALTER TABLE tb_radios ADD COLUMN drive_folder_name TEXT;

-- 🔹 Atualiza timestamps automaticamente em novas alterações
CREATE TRIGGER IF NOT EXISTS trg_update_tb_config_drive
AFTER UPDATE ON tb_config_drive
BEGIN
  UPDATE tb_config_drive SET updated_at = datetime('now') WHERE id_config = NEW.id_config;
END;

CREATE TRIGGER IF NOT EXISTS trg_update_tb_radios
AFTER UPDATE ON tb_radios
BEGIN
  UPDATE tb_radios SET updated_at = datetime('now') WHERE id_radio = NEW.id_radio;
END;
"""

# Caminho para o banco de dados
db_path = "usuarios.db"

conn = sqlite3.connect(db_path)

try:
    conn.executescript(sql_commands)
    conn.commit()
    print("✅ Banco de dados atualizado com sucesso:")
    print("   - Tabela tb_config_drive criada/atualizada")
    print("   - Campos tipo_pasta, drive_folder_id e drive_folder_name adicionados à tb_radios")
except Exception as e:
    print(f"❌ Erro ao atualizar o banco: {e}")
finally:
    conn.close()
