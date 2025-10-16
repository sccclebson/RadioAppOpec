# mod_auth/ldap_utils.py
import os
import ldap3
from ldap3.core.exceptions import LDAPBindError, LDAPExceptionError

LDAP_SERVER = os.getenv("LDAP_SERVER", "ldap://10.14.0.127")
LDAP_DOMAIN = os.getenv("LDAP_DOMAIN", "SCCLGS")  # seu NetBIOS (DOMÍNIO\usuario)
LDAP_TIMEOUT = int(os.getenv("LDAP_TIMEOUT", "5"))

def autenticar_ldap(usuario: str, senha: str) -> bool:
    """Autentica usuário no AD (LDAP). Retorna True/False sem estourar exceção na view."""
    try:
        # Server com timeout para não travar a requisição
        server = ldap3.Server(LDAP_SERVER, get_info=ldap3.NONE, connect_timeout=LDAP_TIMEOUT)

        # Conexão sem auto_bind para podermos tratar o retorno de bind()
        conn = ldap3.Connection(server, user=f"{LDAP_DOMAIN}\\{usuario}", password=senha, auto_bind=False)

        if not conn.bind():           # False quando usuário/senha inválidos
            # opcional: print(conn.result) para logar detalhes
            return False

        conn.unbind()
        return True

    except LDAPBindError:
        # credenciais inválidas ou não foi possível fazer bind
        return False
    except LDAPExceptionError:
        # outros erros do ldap3 (rede, TLS, etc.)
        return False
    except Exception as e:
        # último recurso: não propagar erro para a view
        print(f"[LDAP] Erro inesperado: {e}")
        return False
