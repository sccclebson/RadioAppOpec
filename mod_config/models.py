import sqlite3
import os
import platform
from typing import Optional, List, Dict

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'usuarios.db')

def _conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ============================================================
# 🔧 CONFIGURAÇÕES DO SISTEMA
# ============================================================
class ConfigSistema:
    @staticmethod
    def get() -> Dict:
        with _conn() as c:
            cur = c.execute("""
                SELECT id, secret_key, cache_intervalo_min, max_por_pagina
                FROM tb_config_sistema WHERE id=1
            """)
            row = cur.fetchone()
            if not row:
                return {"id": 1, "secret_key": None, "cache_intervalo_min": 10, "max_por_pagina": 20}
            return dict(row)

    @staticmethod
    def save(secret_key: Optional[str], cache_intervalo_min: int, max_por_pagina: int):
        with _conn() as c:
            c.execute("""
                INSERT INTO tb_config_sistema (id, secret_key, cache_intervalo_min, max_por_pagina)
                VALUES (1, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  secret_key=excluded.secret_key,
                  cache_intervalo_min=excluded.cache_intervalo_min,
                  max_por_pagina=excluded.max_por_pagina
            """, (secret_key, cache_intervalo_min, max_por_pagina))


# ============================================================
# 🧠 CONFIGURAÇÃO DE LDAP
# ============================================================
class ConfigLDAP:
    @staticmethod
    def get_ativa() -> Optional[Dict]:
        with _conn() as c:
            cur = c.execute("""
                SELECT * FROM tb_config_ldap
                WHERE status='ativo'
                ORDER BY updated_at DESC
                LIMIT 1
            """)
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def save(data: Dict):
        with _conn() as c:
            c.execute("""
                INSERT INTO tb_config_ldap
                (servidor, porta, dominio, usuario_base, usuario_bind, senha_bind, usar_ssl, timeout, status, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                data.get('servidor'),
                int(data.get('porta', 389)),
                data.get('dominio'),
                data.get('usuario_base'),
                data.get('usuario_bind'),
                data.get('senha_bind'),
                1 if str(data.get('usar_ssl', '0')).lower() in ('1', 'on', 'true') else 0,
                int(data.get('timeout', 5)),
                data.get('status', 'ativo')
            ))


# ============================================================
# 📻 CONFIGURAÇÕES DE RÁDIOS (com Drive)
# ============================================================
class ConfigRadio:
    @staticmethod
    def select_all() -> List[Dict]:
        with _conn() as c:
            cur = c.execute("SELECT * FROM tb_radios ORDER BY nome")
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_ativas() -> List[Dict]:
        with _conn() as c:
            cur = c.execute("SELECT * FROM tb_radios WHERE ativa=1 ORDER BY nome")
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def by_id(id_radio: int) -> Optional[Dict]:
        with _conn() as c:
            cur = c.execute("SELECT * FROM tb_radios WHERE id_radio=?", (id_radio,))
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def save(data: Dict):
        with _conn() as c:
            c.execute("""
                INSERT INTO tb_radios
                (chave, nome, pasta_base, extensao, parse_nome, ativa,
                 tipo_pasta, drive_folder_id, drive_folder_name,
                 created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                data.get('chave'),
                data.get('nome'),
                data.get('pasta_base'),
                data.get('extensao', '.mp3'),
                data.get('parse_nome'),
                1 if str(data.get('ativa', '1')).lower() in ('1', 'on', 'true') else 0,
                data.get('tipo_pasta', 'local'),
                data.get('drive_folder_id'),
                data.get('drive_folder_name')
            ))

    @staticmethod
    def update(id_radio: int, data: Dict):
        with _conn() as c:
            c.execute("""
                UPDATE tb_radios
                SET chave=?, nome=?, pasta_base=?, extensao=?, parse_nome=?, ativa=?,
                    tipo_pasta=?, drive_folder_id=?, drive_folder_name=?, updated_at=datetime('now')
                WHERE id_radio=?
            """, (
                data.get('chave'),
                data.get('nome'),
                data.get('pasta_base'),
                data.get('extensao', '.mp3'),
                data.get('parse_nome'),
                1 if str(data.get('ativa', '1')).lower() in ('1', 'on', 'true') else 0,
                data.get('tipo_pasta', 'local'),
                data.get('drive_folder_id'),
                data.get('drive_folder_name'),
                id_radio
            ))

    @staticmethod
    def delete(id_radio: int):
        with _conn() as c:
            c.execute("DELETE FROM tb_radios WHERE id_radio=?", (id_radio,))


# ============================================================
# ⚙️ FUNÇÃO GLOBAL: CARREGAR CONFIGURAÇÃO DE RÁDIOS
# ============================================================
def carregar_radios_config() -> Dict[str, Dict]:
    """Carrega rádios ativas e corrige automaticamente caminhos vazios."""
    cfg = {}
    sistema = platform.system().lower()

    if sistema == "windows":
        base_dir = "C:/SCC/RadioAppOpec/uploads"
    else:
        base_dir = "/mnt"

    print(f"🧩 Sistema detectado: {sistema}")

    for r in ConfigRadio.get_ativas():
        if r.get("tipo_pasta") == "drive":
            pasta = f"[Google Drive] {r.get('drive_folder_name') or 'Sem pasta vinculada'}"
        else:
            pasta = r.get("pasta_base") or os.path.join(base_dir, f"{r['chave']}_fm")

        pasta = os.path.normpath(pasta)
        cfg[r["chave"]] = {
            "nome": r["nome"],
            "pasta_base": pasta,
            "extensao": r.get("extensao") or ".mp3",
            "parse_nome": r.get("parse_nome"),
        }

        print(f"📂 {r['nome']} → {pasta}")

    return cfg


# ============================================================
# ☁️ CONFIGURAÇÃO GOOGLE DRIVE
# ============================================================
class ConfigGoogleDrive:
    @staticmethod
    def get() -> Optional[Dict]:
        with _conn() as c:
            cur = c.execute("SELECT * FROM tb_config_drive ORDER BY id_config DESC LIMIT 1")
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def save(client_id: str, client_secret: str, access_token: Optional[str] = None,
             refresh_token: Optional[str] = None, token_expiry: Optional[str] = None,
             user_email: Optional[str] = None):
        with _conn() as c:
            c.execute("""
                INSERT INTO tb_config_drive
                (client_id, client_secret, access_token, refresh_token, token_expiry, user_email, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (client_id, client_secret, access_token, refresh_token, token_expiry, user_email))

    @staticmethod
    def update_tokens(access_token: str, refresh_token: str, token_expiry: str, user_email: str):
        with _conn() as c:
            c.execute("""
                UPDATE tb_config_drive
                SET access_token=?, refresh_token=?, token_expiry=?, user_email=?, updated_at=datetime('now')
                WHERE id_config = (SELECT id_config FROM tb_config_drive ORDER BY id_config DESC LIMIT 1)
            """, (access_token, refresh_token, token_expiry, user_email))
