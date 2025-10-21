import os
from datetime import datetime

def listar_audios(radio_cfg, data=None, hora_ini=None, hora_fim=None):
    """Lista arquivos de áudio da pasta local (recursivamente), filtrando por extensão."""
    pasta_base = radio_cfg.get("pasta_base")

    # Lê o campo "extensao" e normaliza para remover ponto, espaços e vírgulas
    ext_raw = radio_cfg.get("extensao", ".mp3").lower().strip()
    if not ext_raw:
        ext_raw = "mp3"

    # Divide por vírgula caso tenha várias e remove "." se existir
    extensoes = [e.strip().lstrip(".") for e in ext_raw.split(",") if e.strip()]
    print(f"🎧 [CACHE] Extensões válidas para {radio_cfg.get('nome', '?')}: {extensoes}")

    if not os.path.exists(pasta_base):
        print(f"⚠️ [CACHE] Caminho inexistente: {pasta_base}")
        return []

    print(f"🎧 [CACHE] Iniciando varredura recursiva em: {pasta_base}")



    audios = []
    for root, dirs, files in os.walk(pasta_base):
        if dirs:
            for d in dirs:
                print(f"📁 Descendo na subpasta: {d}")
        for file in files:
            nome_arquivo = file.lower()
            # Filtra pela extensão
            if not any(nome_arquivo.endswith(f".{ext}") for ext in extensoes):
                continue

            caminho = os.path.join(root, file)
            try:
                stat = os.stat(caminho)
                datahora = datetime.fromtimestamp(stat.st_mtime)
                # --- FILTRO POR DATA / HORA ---
                if data:
                    try:
                        data_filtro = datetime.strptime(data, "%Y-%m-%d").date()
                        if datahora.date() != data_filtro:
                            continue
                    except Exception:
                        pass

                if hora_ini or hora_fim:
                    try:
                        h_ini = datetime.strptime(hora_ini or "00:00", "%H:%M").time()
                        h_fim = datetime.strptime(hora_fim or "23:59", "%H:%M").time()
                        if not (h_ini <= datahora.time() <= h_fim):
                            continue
                    except Exception:
                        pass
                # -------------------------------
                tamanho_kb = stat.st_size / 1024

                audios.append({
                    "nome": file,
                    "datahora": datahora.strftime("%d/%m/%Y %H:%M:%S"),
                    "tamanho": f"{tamanho_kb:,.0f} KB",
                    "caminho": caminho
                })
            except Exception as e:
                print(f"⚠️ Erro ao ler arquivo '{file}': {e}")

    print(f"✅ [CACHE] {len(audios)} arquivos encontrados em {pasta_base}")
    print(f"💾 [CACHE] Atualização concluída → {radio_cfg.get('nome', radio_cfg.get('chave', '?'))} ({len(audios)} arquivos, extensões {extensoes})")


    return sorted(audios, key=lambda x: x["datahora"], reverse=True)
