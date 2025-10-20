import os
from flask import Flask, render_template
from mod_radio.routes import bp_radio
from mod_auth.routes import bp_auth
from mod_admin.routes import bp_admin
from mod_config import bp_config
from mod_config.models import ConfigSistema
from mod_radio.audio_cache import iniciar_cache_automatico

# ============================================================
# 🎛️ Criação da aplicação Flask
# ============================================================
app = Flask(__name__)

# ---------- CONFIGURAÇÃO DINÂMICA ----------
# SECRET_KEY: prioridade ENV > BD > fallback dev
app.config["SECRET_KEY"] = (
    os.getenv("SECRET_KEY")
    or (ConfigSistema.get().get("secret_key") or "dev-secret")
)

# ---------- BANCO DE DADOS ----------
# (mantém o SQLite padrão, compatível com Windows e Linux)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///usuarios.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ============================================================
# 🔗 REGISTRO DOS BLUEPRINTS
# ============================================================
app.register_blueprint(bp_radio)
app.register_blueprint(bp_auth)
app.register_blueprint(bp_admin)
app.register_blueprint(bp_config)

# ============================================================
# ⚠️ HANDLERS DE ERRO COMUM
# ============================================================
@app.errorhandler(403)
def e403(_e):
    return render_template("error_403.html"), 403


# ============================================================
# 🚀 ENTRYPOINT PRINCIPAL
# ============================================================
if __name__ == "__main__":
    # Carrega o intervalo de cache configurado
    sistema = ConfigSistema.get()
    intervalo = int(sistema.get("cache_intervalo_min", 10))

    # Inicia o cache automático em thread separada
    print(f"🕒 Atualização automática de cache iniciada ({intervalo}min)")
    iniciar_cache_automatico(intervalo)

    # Mensagem clara de inicialização
    print("🚀 Sistema iniciado com sucesso! Acesse: http://127.0.0.1:5000")

    # Executa o Flask
    app.run(
        host="0.0.0.0",  # permite acesso remoto (útil em VMs ou Proxmox)
        port=5000,
        debug=True,
        use_reloader=True  # mantém o auto reload ativo
    )
