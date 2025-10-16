# mod_admin/routes.py
from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from .models import listar_logins, listar_usuarios, contar_usuarios, contar_logins, get_connection
from mod_auth.utils import admin_required

bp_admin = Blueprint('admin', __name__, template_folder='templates')

@bp_admin.route('/admin/dashboard')
@admin_required   # ✅ Decorator direto
def dashboard():
    """Painel de controle com estatísticas"""

    total_usuarios = contar_usuarios()
    logins = contar_logins()
    total_local = logins.get("local", 0)
    total_ldap = logins.get("ldap", 0)

    logs = listar_logins(10)
    usuarios = listar_usuarios()

    return render_template(
        'admin_dashboard.html',
        total_usuarios=total_usuarios,
        total_local=total_local,
        total_ldap=total_ldap,
        logs=logs,
        usuarios=usuarios
    )


@bp_admin.route('/admin/usuarios')
@admin_required
def usuarios():
    print("🔍 Acessando rota /admin/usuarios")  # Debug
    from .models import listar_usuarios
    usuarios = listar_usuarios()
    usuarios = [dict(u) for u in usuarios]  # ✅ converte sqlite3.Row para dict

    print(f"✅ Usuários retornados: {usuarios}")

    return render_template('admin_usuarios.html', usuarios=usuarios)




@bp_admin.route('/admin/logins')
@admin_required
def logins():
    """Mostra histórico completo de logins"""

    logs = listar_logins(100)
    return render_template('admin_logins.html', logs=logs)



from werkzeug.security import generate_password_hash
from .models import (
    listar_usuarios, obter_usuario_por_id, criar_usuario, atualizar_usuario, excluir_usuario
)

# ➕ Novo usuário
@bp_admin.route('/admin/usuarios/novo', methods=['GET', 'POST'])
@admin_required
def novo_usuario():
    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        senha = request.form['senha']
        tipo = request.form['tipo']
        senha_hash = generate_password_hash(senha)

        criar_usuario(nome, usuario, senha_hash, tipo)
        flash('Usuário criado com sucesso!', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template('admin_usuario_form.html', titulo="Novo Usuário")


# ✏️ Editar usuário
@bp_admin.route('/admin/usuarios/<int:user_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar_usuario(user_id):
    user = obter_usuario_por_id(user_id)
    if not user:
        flash('Usuário não encontrado.', 'danger')
        return redirect(url_for('admin.usuarios'))

    if request.method == 'POST':
        nome = request.form['nome']
        usuario = request.form['usuario']
        tipo = request.form['tipo']

        atualizar_usuario(user_id, nome, usuario, tipo)
        flash('Usuário atualizado com sucesso!', 'success')
        return redirect(url_for('admin.usuarios'))

    return render_template('admin_usuario_form.html', titulo="Editar Usuário", user=user)


# 🗑️ Excluir usuário
@bp_admin.route('/admin/usuarios/<int:user_id>/excluir', methods=['POST'])
@admin_required
def excluir_usuario_route(user_id):
    excluir_usuario(user_id)
    flash('Usuário excluído com sucesso!', 'info')
    return redirect(url_for('admin.usuarios'))
