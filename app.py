import os
from flask import Flask, render_template
from mod_radio.routes import bp_radio
from mod_auth.routes import bp_auth
from mod_admin.routes import bp_admin
from mod_config import bp_config
from mod_config.models import ConfigSistema
from mod_radio.audio_cache import inicializar_cache  # ✅ novo import

from dotenv import load_dotenv
load_dotenv()

# ============================================================
# 🎛️ Criação da aplicação Flask
# ============================================================
app = Flask(__name__)

app.config["SECRET_KEY"] = (
    os.getenv("SECRET_KEY")
    or (ConfigSistema.get().get("secret_key") or "dev-secret")
)

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
    # Inicializa o cache (carrega local + Drive persistente)
    inicializar_cache()
    print("🚀 Sistema iniciado com sucesso! Acesse: http://127.0.0.1:5000")

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=True,
        use_reloader=True
    )
