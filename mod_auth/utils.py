from functools import wraps
from flask import current_app, session, redirect, url_for, flash, render_template

def login_required(f):
    """Exige login de qualquer tipo de usuário (local ou LDAP)."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash("⚠️ Você precisa estar logado para acessar esta página.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Exige login e perfil admin — renderiza erro 403 se não for admin."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = session.get('user')
        if not user:
            flash("⚠️ Faça login para continuar.", "warning")
            return redirect(url_for('auth.login'))

        # 🚫 Se o usuário logado não for admin, mostra página 403
        if user.get('tipo') != 'admin':
            template = current_app.jinja_env.get_or_select_template("error_403.html")
            return template.render(user=user), 403

        # ✅ Se for admin, segue normalmente
        return f(*args, **kwargs)
    return decorated_function
