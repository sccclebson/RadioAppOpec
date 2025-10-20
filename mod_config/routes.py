import os
from flask import render_template, request, redirect, url_for, flash, jsonify
from . import bp_config
from .models import ConfigLDAP, ConfigRadio, ConfigSistema, carregar_radios_config
from mod_auth.utils import admin_required
from mod_auth.ldap_utils import testar_conexao_ldap

@bp_config.route('/')
@admin_required
def dashboard():
    sistemas = ConfigSistema.get()
    return render_template('config_dashboard.html', sistemas=sistemas)

# ---------- SISTEMA ----------
@bp_config.route('/sistema', methods=['GET', 'POST'])
@admin_required
def config_sistema():
    if request.method == 'POST':
        secret_key = request.form.get('secret_key') or None
        cache_intervalo_min = int(request.form.get('cache_intervalo_min', 10))
        max_por_pagina = int(request.form.get('max_por_pagina', 20))
        ConfigSistema.save(secret_key, cache_intervalo_min, max_por_pagina)
        flash('Configurações do sistema salvas.', 'success')
        return redirect(url_for('bp_config.config_sistema'))
    sistemas = ConfigSistema.get()
    return render_template('config_sistema.html', sistemas=sistemas)

# ---------- LDAP ----------
@bp_config.route('/ldap', methods=['GET', 'POST'])
@admin_required
def config_ldap():
    if request.method == 'POST':
        ConfigLDAP.save(request.form)
        flash('Configuração LDAP registrada.', 'success')
        return redirect(url_for('bp_config.config_ldap'))
    ldap = ConfigLDAP.get_ativa()
    return render_template('config_ldap.html', ldap=ldap)

@bp_config.route('/ldap/test', methods=['POST'])
@admin_required
def ldap_test():
    ok, msg = testar_conexao_ldap(request.form.to_dict())
    return jsonify({'ok': ok, 'mensagem': msg}), (200 if ok else 400)

# ---------- RÁDIOS ----------
@bp_config.route('/radios')
@admin_required
def radios():
    radios = ConfigRadio.select_all()
    return render_template('config_radios.html', radios=radios)

@bp_config.route('/radios/add', methods=['POST'])
@admin_required
def add_radio():
    ConfigRadio.save(request.form)
    flash('Rádio adicionada.', 'success')
    return redirect(url_for('bp_config.radios'))

@bp_config.route('/radios/edit/<int:id_radio>', methods=['POST'])
@admin_required
def edit_radio(id_radio):
    ConfigRadio.update(id_radio, request.form)
    flash('Rádio atualizada.', 'success')
    return redirect(url_for('bp_config.radios'))

@bp_config.route('/radios/delete/<int:id_radio>', methods=['POST'])
@admin_required
def delete_radio(id_radio):
    ConfigRadio.delete(id_radio)
    flash('Rádio removida.', 'danger')
    return redirect(url_for('bp_config.radios'))

@bp_config.route('/radios/test-path', methods=['POST'])
@admin_required
def test_path():
    path = request.form.get('pasta_base', '')
    ok = os.path.isdir(path)
    return jsonify({'ok': ok, 'mensagem': 'Diretório existe.' if ok else 'Diretório não encontrado.'}), (200 if ok else 400)