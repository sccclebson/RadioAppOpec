import os
from flask import render_template, request, redirect, url_for, flash, jsonify, session
from . import bp_config
from .models import (
    ConfigLDAP, ConfigRadio, ConfigSistema,
    carregar_radios_config, ConfigGoogleDrive, get_media_drive_dir
)
from mod_auth.utils import admin_required
from mod_auth.ldap_utils import testar_conexao_ldap
from mod_config.google_drive_utils import (
    create_flow, build_drive_service, sincronizar_pasta_drive_para_local
)
import requests


# ============================================================
# ⚙️ DASHBOARD
# ============================================================
@bp_config.route('/')
@admin_required
def dashboard():
    sistemas = ConfigSistema.get()
    return render_template('config_dashboard.html', sistemas=sistemas)


# ============================================================
# ⚙️ CONFIGURAÇÃO DO SISTEMA
# ============================================================
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


# ============================================================
# 🔐 CONFIGURAÇÃO LDAP
# ============================================================
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


# ============================================================
# 📻 CONFIGURAÇÃO DE RÁDIOS
# ============================================================
@bp_config.route('/radios')
@admin_required
def radios():
    radios = ConfigRadio.select_all()
    return render_template('config_radios.html', radios=radios)


@bp_config.route('/radios/add', methods=['POST'])
@admin_required
def add_radio():
    """Adiciona uma nova rádio (local ou Google Drive)."""
    tipo_pasta = request.form.get("tipo_pasta")
    drive_folder_id = request.form.get("drive_folder_id")
    drive_folder_name = None
    pasta_base = request.form.get("pasta_base")

    # Se for uma pasta do Google Drive, buscar o nome via API
    if tipo_pasta == "drive" and drive_folder_id:
        from mod_config.google_drive_utils import build_drive_service
        config = ConfigGoogleDrive.get()

        if config:
            try:
                service = build_drive_service(config)
                folder = service.files().get(fileId=drive_folder_id, fields="id, name").execute()
                drive_folder_name = folder["name"]
                pasta_base = f"[Google Drive] {drive_folder_name}"
            except Exception as e:
                print("❌ Erro ao buscar nome da pasta do Drive:", e)
                flash("Não foi possível buscar o nome da pasta do Google Drive.", "danger")

    # Monta os dados a serem salvos
    data = {
        "chave": request.form.get("chave"),
        "nome": request.form.get("nome"),
        "pasta_base": pasta_base,
        "extensao": request.form.get("extensao", ".mp3"),
        "parse_nome": request.form.get("parse_nome"),
        "ativa": "ativa" in request.form,
        "tipo_pasta": tipo_pasta,
        "drive_folder_id": drive_folder_id,
        "drive_folder_name": drive_folder_name,
    }

    ConfigRadio.save(data)
    flash("✅ Rádio adicionada com sucesso!", "success")
    return redirect(url_for("bp_config.radios"))





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


# ============================================================
# ☁️ INTEGRAÇÃO COM GOOGLE DRIVE
# ============================================================
@bp_config.route("/config/google-drive", methods=["GET", "POST"])
@admin_required
def config_google_drive():
    """Tela principal da integração com o Google Drive."""
    config = ConfigGoogleDrive.get()

    if request.method == "POST":
        client_id = request.form.get("client_id")
        client_secret = request.form.get("client_secret")

        if not client_id or not client_secret:
            flash("Preencha Client ID e Client Secret.", "warning")
            return redirect(url_for("bp_config.config_google_drive"))

        if config:
            ConfigGoogleDrive.save(client_id, client_secret,
                                   access_token=config.get("access_token"),
                                   refresh_token=config.get("refresh_token"),
                                   token_expiry=config.get("token_expiry"),
                                   user_email=config.get("user_email"))
        else:
            ConfigGoogleDrive.save(client_id, client_secret)

        flash("Credenciais salvas com sucesso! Clique em Conectar ao Google Drive.", "info")
        return redirect(url_for("bp_config.config_google_drive"))

    return render_template("config_google_drive.html", config=config)


@bp_config.route("/config/google-drive/connect")
@admin_required
def google_drive_connect():
    """Inicia o fluxo de autenticação OAuth com o Google."""
    config = ConfigGoogleDrive.get()
    if not config:
        flash("Configure o Client ID e Secret antes de conectar.", "warning")
        return redirect(url_for("bp_config.config_google_drive"))

    redirect_uri = url_for(".google_drive_callback", _external=True)
    print("🔗 redirect_uri:", redirect_uri)

    flow = create_flow(config["client_id"], config["client_secret"], redirect_uri)
    auth_url, _ = flow.authorization_url(
        prompt="consent",
        access_type="offline",
        include_granted_scopes="true"
    )

    session["state"] = str(getattr(flow.oauth2session, "state", ""))
    return redirect(auth_url)


@bp_config.route("/config/google-drive/callback")
@admin_required
def google_drive_callback():
    """Callback do Google após autenticação bem-sucedida."""
    config = ConfigGoogleDrive.get()
    if not config:
        flash("Configuração do Google Drive não encontrada.", "danger")
        return redirect(url_for("bp_config.config_google_drive"))

    redirect_uri = url_for(".google_drive_callback", _external=True)
    flow = create_flow(config["client_id"], config["client_secret"], redirect_uri)
    flow.fetch_token(authorization_response=request.url)

    creds = flow.credentials  # credenciais obtidas

    # --- Obter o e-mail da conta autenticada ---
    from googleapiclient.discovery import build
    try:
        service = build("drive", "v3", credentials=creds)
        about = service.about().get(fields="user").execute()
        user_email = about["user"]["emailAddress"]
    except Exception:
        user_email = "desconhecido"

    # --- Atualiza tokens no banco ---
    ConfigGoogleDrive.update_tokens(
        access_token=creds.token,
        refresh_token=creds.refresh_token,
        token_expiry=str(creds.expiry),
        user_email=user_email
    )

    flash(f"✅ Conectado ao Google Drive como {user_email}", "success")
    return redirect(url_for("bp_config.config_google_drive"))


# ============================================================
# 📂 LISTAR PASTAS DO GOOGLE DRIVE
# ============================================================
@bp_config.route("/config/google-drive/folders")
@admin_required
def google_drive_folders():
    """Retorna lista de pastas do Google Drive autenticado."""
    config = ConfigGoogleDrive.get()
    if not config or not config.get("access_token"):
        return jsonify({"ok": False, "pastas": [], "msg": "Google Drive não conectado."}), 400

    try:
        service = build_drive_service(config)
        results = service.files().list(
            q="mimeType='application/vnd.google-apps.folder' and trashed=false",
            fields="files(id, name, parents)"
        ).execute()
        pastas = results.get("files", [])
        return jsonify({"ok": True, "pastas": pastas})
    except Exception as e:
        return jsonify({"ok": False, "pastas": [], "msg": str(e)}), 500
    

# ============================================================
# ☁️ SINCRONIZAÇÃO DE PASTA DO GOOGLE DRIVE
# ============================================================
@bp_config.route("/config/sincronizar-drive/<int:id_radio>")
@admin_required
def sincronizar_drive(id_radio):
    """Sincroniza os arquivos da pasta do Google Drive com o diretório local."""
    try:
        radio = ConfigRadio.by_id(id_radio)
        if not radio:
            flash("Rádio não encontrada.", "danger")
            return redirect(url_for("bp_config.radios"))

        if not radio.get("drive_folder_id"):
            flash("Esta rádio não possui pasta vinculada ao Google Drive.", "warning")
            return redirect(url_for("bp_config.radios"))

        cfg_drive = ConfigGoogleDrive.get()
        if not cfg_drive:
            flash("Google Drive não configurado.", "warning")
            return redirect(url_for("bp_config.config_google_drive"))

        service = build_drive_service(cfg_drive)
        destino = os.path.join(get_media_drive_dir(), radio["nome"].replace(" ", "_"))
        total = sincronizar_pasta_drive_para_local(service, radio["drive_folder_id"], destino)

        flash(f"✅ {total} arquivos sincronizados da rádio '{radio['nome']}'!", "success")
        print(f"📦 Sincronização concluída → {destino}")
    except Exception as e:
        flash(f"Erro ao sincronizar com o Drive: {e}", "danger")
        print("❌ Erro de sincronização:", e)

    return redirect(url_for("bp_config.radios"))