from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from mod_auth.models import salvar_usuario, buscar_usuario  # ✅ sem Usuario
from mod_auth.ldap_utils import autenticar_ldap
from mod_admin.models import registrar_login  # ✅ Import do log

bp_auth = Blueprint('auth', __name__, template_folder='templates')

@bp_auth.route('/')
def index():
    # Se já estiver logado, envia para o painel principal
    if 'user' in session:
        if session['user']['tipo'] == 'admin':
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('radio.select_radio'))
    # Se não estiver logado, mostra a tela de login
    return redirect(url_for('auth.login'))


@bp_auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        # 1️⃣ Tenta autenticação local via SQLite
        user = buscar_usuario(usuario)
        if user and check_password_hash(user['senha'], senha):
            session['user'] = {"usuario": user['usuario'], "tipo": user['tipo']}

            # ✅ REGISTRO DE LOGIN LOCAL
            registrar_login(usuario, "local", request.remote_addr)

            flash(f"Bem-vindo, {user['nome']}!", "success")
            return redirect(url_for('radio.select_radio'))

        # 2️⃣ Se falhar, tenta autenticação LDAP
        elif autenticar_ldap(usuario, senha):
            session['user'] = {"usuario": usuario, "tipo": "colaborador"}

            # ✅ REGISTRO DE LOGIN LDAP
            registrar_login(usuario, "ldap", request.remote_addr)

            flash(f"Autenticado via LDAP: {usuario}", "info")
            return redirect(url_for('radio.select_radio'))

        # 3️⃣ Caso contrário
        flash("Usuário ou senha inválidos.", "danger")

    return render_template('login.html')


@bp_auth.route('/logout')
def logout():
    session.pop('user', None)
    flash("Você saiu do sistema.", "info")
    return redirect(url_for('auth.login'))


@bp_auth.route('/admin/setup')
def setup_admin():
    """Cria um usuário admin padrão, caso não exista."""
    user = buscar_usuario('admin')
    if user:
        return "⚠️ Usuário 'admin' já existe.", 400

    novo_usuario = {
        "nome": "Administrador do Sistema",
        "usuario": "admin",
        "senha": generate_password_hash("1234"),  # senha inicial
        "tipo": "admin"
    }
    salvar_usuario(novo_usuario)

    return "✅ Usuário 'admin' criado com sucesso! (login: admin / senha: 1234)"
