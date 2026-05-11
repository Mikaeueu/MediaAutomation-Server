"""Verificacao e download de atualizacoes via Supabase + Google Drive.

Tabela esperada no Supabase (``app_versions``):
    - version          TEXT  (semver: '0.7.2')
    - download_url     TEXT  (link de share do Google Drive)
    - release_notes    TEXT  (opcional)
    - mandatory        BOOL
    - created_at       TIMESTAMPTZ

A anon key e segura distribuir junto do exe (RLS limita a SELECT publico).
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Callable

import requests

from launcher.version import __version__

# ============================================================
# Configuracao - lida de variaveis de ambiente.
# Em modo dev: .env tem SUPABASE_URL e SUPABASE_ANON_KEY.
# Em modo frozen (exe): user pode definir variaveis no Windows OU
# editar este arquivo direto antes de buildar.
# ============================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://xnlhenroaioltnsyctib.supabase.co")
SUPABASE_ANON_KEY = os.environ.get("SUPABASE_ANON_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InhubGhlbnJvYWlvbHRuc3ljdGliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Nzc4MTEzMTgsImV4cCI6MjA5MzM4NzMxOH0.P54iH1vltaQLzIwMu-2bTz9PsnCC8qWPDEDIIVjCicI")


class UpdateError(RuntimeError):
    """Erro generico do updater."""


def _parse_version(v: str) -> tuple[int, ...]:
    """Converte '1.2.3' em (1, 2, 3) para comparacao tupla."""
    parts = re.split(r"[.\-+]", (v or "0").strip())
    out: list[int] = []
    for p in parts:
        if p.isdigit():
            out.append(int(p))
        else:
            break
    return tuple(out) if out else (0,)


def check_for_updates() -> dict | None:
    """Consulta a versao mais recente no Supabase.

    Returns:
        Dict com a versao remota (campos: version, download_url,
        release_notes, mandatory) se for mais nova que a local;
        ``None`` se ja esta atualizado.

    Raises:
        UpdateError: Se a config do Supabase esta vazia ou o request falha.
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise UpdateError(
            "SUPABASE_URL e SUPABASE_ANON_KEY nao estao configurados. "
            "Adicione no .env (dev) ou edite launcher/updater.py antes "
            "de buildar."
        )

    url = f"{SUPABASE_URL.rstrip('/')}/rest/v1/app_versions"
    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    }
    params = {"select": "*", "order": "created_at.desc", "limit": "1"}

    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UpdateError(f"Falha ao consultar Supabase: {exc}") from exc

    data = response.json()
    if not data:
        return None

    latest = data[0]
    remote_v = _parse_version(latest.get("version", ""))
    local_v = _parse_version(__version__)
    if remote_v <= local_v:
        return None
    return latest


def transform_drive_url(share_url: str) -> str:
    """Converte URL de compartilhamento do Drive em URL de download direto.

    Suporta dois formatos comuns:
      * ``https://drive.google.com/file/d/FILE_ID/view``
      * ``https://drive.google.com/open?id=FILE_ID``

    Outros formatos (incluindo URLs nao-Drive) sao retornados intactos.
    """
    if "drive.google.com" not in share_url:
        return share_url
    if "/file/d/" in share_url:
        file_id = share_url.split("/file/d/")[1].split("/")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    if "id=" in share_url:
        file_id = share_url.split("id=")[1].split("&")[0]
        return f"https://drive.google.com/uc?export=download&id={file_id}"
    return share_url


def download_update(
    download_url: str,
    target: Path,
    progress_cb: Callable[[int, int], None] | None = None,
) -> Path:
    """Baixa o instalador da nova versao.

    Args:
        download_url: URL do download (link Drive ou direto).
        target: Caminho destino do arquivo.
        progress_cb: Callback opcional ``(bytes_baixados, total_bytes)``.

    Returns:
        Path do arquivo baixado.

    Raises:
        UpdateError: Se o download falhar.
    """
    direct = transform_drive_url(download_url)
    try:
        response = requests.get(direct, stream=True, timeout=30, allow_redirects=True)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise UpdateError(f"Falha ao baixar: {exc}") from exc

    total = int(response.headers.get("content-length", 0))
    target.parent.mkdir(parents=True, exist_ok=True)
    downloaded = 0
    with open(target, "wb") as fp:
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            fp.write(chunk)
            downloaded += len(chunk)
            if progress_cb:
                try:
                    progress_cb(downloaded, total)
                except Exception:  # noqa: BLE001
                    pass
    return target


def default_download_target(version: str) -> Path:
    """Retorna onde salvar o instalador baixado (pasta Downloads do user)."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        downloads = Path.home()
    return downloads / f"MediaAutomationServer-Setup-{version}.exe"
