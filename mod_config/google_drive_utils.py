# mod_config/google_drive_utils.py
import os
import io
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

def create_flow(client_id, client_secret, redirect_uri):
    """Cria o fluxo OAuth 2.0."""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uris": [redirect_uri],
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=SCOPES,
    )
    flow.redirect_uri = redirect_uri
    return flow


def build_drive_service(tokens):
    """Cria o serviço autenticado do Google Drive."""
    creds = Credentials(
        tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=tokens["client_id"],
        client_secret=tokens["client_secret"],
        scopes=SCOPES,
    )

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    elif creds.expired:
        raise RuntimeError("Token expirado e sem refresh_token disponível.")

    return build("drive", "v3", credentials=creds)


def sincronizar_pasta_drive_para_local(service, folder_id, destino_local, nivel=0):
    """
    Baixa todos os arquivos de áudio de uma pasta e suas subpastas do Google Drive.
    Mantém a mesma estrutura de diretórios localmente.
    """
    import time
    from googleapiclient.http import MediaIoBaseDownload

    os.makedirs(destino_local, exist_ok=True)
    indent = "  " * nivel
    total = 0

    print(f"{indent}📂 Varredura: {destino_local}")

    # --- 1️⃣ Listar arquivos de áudio na pasta atual ---
    query_files = f"'{folder_id}' in parents and trashed=false and mimeType contains 'audio/'"
    response_files = service.files().list(
        q=query_files,
        fields="files(id, name, size, modifiedTime)",
        spaces="drive"
    ).execute()

    for f in response_files.get("files", []):
        nome = f["name"]
        local_path = os.path.join(destino_local, nome)

        if not os.path.exists(local_path):
            print(f"{indent}⬇️ Baixando {nome}...")
            request = service.files().get_media(fileId=f["id"])
            with io.FileIO(local_path, "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
                    if status:
                        print(f"{indent}   Progresso: {int(status.progress() * 100)}%")
            total += 1
        else:
            print(f"{indent}✅ Já existe: {nome}")

    # --- 2️⃣ Listar subpastas ---
    query_folders = f"'{folder_id}' in parents and trashed=false and mimeType='application/vnd.google-apps.folder'"
    response_folders = service.files().list(
        q=query_folders,
        fields="files(id, name)",
        spaces="drive"
    ).execute()

    for folder in response_folders.get("files", []):
        sub_nome = folder["name"]
        sub_id = folder["id"]
        sub_dest = os.path.join(destino_local, sub_nome)
        print(f"{indent}📁 Descendo na subpasta: {sub_nome}")
        total += sincronizar_pasta_drive_para_local(service, sub_id, sub_dest, nivel + 1)
        time.sleep(0.3)  # para evitar limite de taxa do Google

    if nivel == 0:
        print(f"🎧 Sincronização concluída: {total} arquivos baixados (incluindo subpastas).")
    return total
