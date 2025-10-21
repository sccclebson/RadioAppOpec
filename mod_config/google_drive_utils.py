# mod_config/google_drive_utils.py
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request

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
    """Cria o serviço autenticado do Drive (quando já temos os tokens)."""
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
