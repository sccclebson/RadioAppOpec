from typing import Tuple, Dict, Optional
from mod_config.models import ConfigLDAP

# Opcional: se ldap3 estiver instalado e configurado no projeto
try:
    from ldap3 import Server, Connection, ALL, Tls
except Exception:  # fallback se não houver ldap3
    Server = Connection = ALL = Tls = None

def obter_config_ldap_ativa() -> Optional[Dict]:
    cfg = ConfigLDAP.get_ativa()
    if not cfg:
        return None
    return {
        "servidor": cfg["servidor"],
        "porta": int(cfg["porta"]),
        "dominio": cfg["dominio"],
        "usuario_base": cfg["usuario_base"],
        "usuario_bind": cfg.get("usuario_bind"),
        "senha_bind": cfg.get("senha_bind"),
        "usar_ssl": bool(cfg.get("usar_ssl")),
        "timeout": int(cfg["timeout"]),
    }

def autenticar_ldap(usuario: str, senha: str) -> Tuple[bool, str]:
    cfg = obter_config_ldap_ativa()
    if not cfg:
        return False, "LDAP não configurado/ativo."

    if Server is None or Connection is None:
        return False, "Dependência ldap3 não disponível no ambiente."

    try:
        server = Server(cfg["servidor"], port=cfg["porta"], use_ssl=cfg["usar_ssl"], get_info=ALL, connect_timeout=cfg["timeout"])
        # Ex.: user@dominio
        user_dn = f"{usuario}@{cfg['dominio']}"
        conn = Connection(server, user=user_dn, password=senha, auto_bind=True)
        try:
            if conn.bound:
                return True, "OK"
            return False, "Falha de autenticação LDAP."
        finally:
            conn.unbind()
    except Exception as e:
        return False, f"Erro LDAP: {e}"

def testar_conexao_ldap(data_form: Dict) -> Tuple[bool, str]:
    if Server is None or Connection is None:
        return False, "Dependência ldap3 não disponível no ambiente."

    servidor = data_form.get("servidor")
    porta = int(data_form.get("porta", 389))
    usar_ssl = str(data_form.get("usar_ssl", "0")).lower() in ("1", "true", "on")
    timeout = int(data_form.get("timeout", 5))
    usuario_bind = data_form.get("usuario_bind")
    senha_bind = data_form.get("senha_bind")
    dominio = data_form.get("dominio")

    try:
        server = Server(servidor, port=porta, use_ssl=usar_ssl, get_info=ALL, connect_timeout=timeout)
        user = f"{usuario_bind}@{dominio}" if usuario_bind and dominio else usuario_bind
        conn = Connection(server, user=user, password=senha_bind, auto_bind=True)
        ok = conn.bound
        conn.unbind()
        return (True, "Conexão realizada com sucesso.") if ok else (False, "Não foi possível estabelecer a conexão.")
    except Exception as e:
        return False, f"Falha: {e}"