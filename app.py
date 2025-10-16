from flask import Flask
from flask import render_template
from mod_radio.routes import bp_radio
from mod_auth.routes import bp_auth
from mod_admin.routes import bp_admin
from mod_radio.audio_cache import iniciar_cache_automatico

iniciar_cache_automatico(10)

app = Flask(__name__)

app.secret_key = 'chave-super-secreta'

@app.errorhandler(403)
def erro_403(e):
    return render_template("error_403.html"), 403

# Banco local (pode ser trocado para MySQL depois)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Blueprints
app.register_blueprint(bp_radio)
app.register_blueprint(bp_auth)
app.register_blueprint(bp_admin)

if __name__ == '__main__':
    app.run(debug=True)
