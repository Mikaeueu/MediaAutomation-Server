"""Entry point do launcher.

Suporta dois modos:

* **GUI (default)**: abre a janela PySide6 + tray icon. O usuario clica
  em "Iniciar servidor" e o launcher dispara um subprocess com este mesmo
  exe rodando em ``--server-mode``.

* **server-mode** (``--server-mode``): roda apenas o uvicorn sem GUI.
  Usado quando o launcher esta empacotado como .exe via PyInstaller, pra
  resolver o problema de ``sys.executable`` apontar pro proprio exe (e
  nao pro python que sabe rodar uvicorn).

Para rodar em desenvolvimento::

    python -m launcher.main

Para empacotar via PyInstaller, ver ``packaging/MediaAutomationServer.spec``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def project_root() -> Path:
    """Determina a raiz do projeto (onde fica ``app/``)."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent.parent


def _arg_value(name: str, default: str) -> str:
    """Le ``--name VALOR`` de ``sys.argv``, default se nao estiver presente."""
    if name in sys.argv:
        idx = sys.argv.index(name)
        if idx + 1 < len(sys.argv):
            return sys.argv[idx + 1]
    return default


def _crash_log_path() -> Path:
    """Path do arquivo de log de crash (pra ver erro quando log nao captura)."""
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    p = Path(base) / "MediaAutomationServer"
    p.mkdir(parents=True, exist_ok=True)
    return p / "server-crash.log"


def run_server_mode() -> int:
    """Executa apenas o uvicorn, sem abrir a janela Qt.

    Tudo envolto em try/except global porque crashes no startup nao
    aparecem no log do subprocess (stdout buffering). O traceback e
    printado E gravado em ``%LOCALAPPDATA%\\MediaAutomationServer\\
    server-crash.log`` pra garantir visibilidade.
    """
    import traceback

    try:
        root = project_root()
        if str(root) not in sys.path:
            sys.path.insert(0, str(root))
        os.chdir(root)

        # Print de diagnostico ANTES dos imports pesados (ajuda a saber
        # ate onde chegou caso quebre).
        print(f"[server-mode] cwd={os.getcwd()}", flush=True)
        print(f"[server-mode] root={root}", flush=True)
        print(f"[server-mode] frozen={getattr(sys, 'frozen', False)}", flush=True)

        import uvicorn  # noqa: PLC0415
        print("[server-mode] uvicorn import OK", flush=True)

        from app.main import app  # noqa: PLC0415
        print("[server-mode] app.main import OK", flush=True)

        host = _arg_value("--host", "0.0.0.0")
        port = int(_arg_value("--port", "8000"))
        print(f"[server-mode] iniciando uvicorn em {host}:{port}", flush=True)

        uvicorn.run(app, host=host, port=port, log_level="info")
        return 0
    except Exception as exc:
        tb = traceback.format_exc()
        msg = f"[server-mode] CRASH: {type(exc).__name__}: {exc}\n\n{tb}\n"
        print(msg, flush=True)
        try:
            with open(_crash_log_path(), "w", encoding="utf-8") as fp:
                fp.write(msg)
        except Exception:
            pass
        return 1


def run_gui_mode() -> int:
    """Inicializa Qt, MainWindow e Tray e roda o event loop.

    Tambem faz ``chdir`` pra raiz do projeto (ou ``_MEIPASS``), porque o
    ServerRunner precisa que paths relativos (``app/``, ``data/``)
    resolvam corretamente ao iniciar o subprocess do uvicorn.
    """
    os.chdir(project_root())

    # Imports tardios pra nao carregar Qt no modo --server-mode.
    from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

    from launcher.main_window import MainWindow
    from launcher.tray import TrayIcon

    qt_app = QApplication(sys.argv)
    qt_app.setQuitOnLastWindowClosed(False)

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(
            None,
            "MediaAutomationServer",
            "System tray nao esta disponivel neste sistema.",
        )
        return 1

    window = MainWindow(project_root=project_root())
    window.show()

    tray = TrayIcon(window)
    tray.show()

    return qt_app.exec()


def main() -> int:
    """Roteador entre GUI e server-only mode."""
    if "--server-mode" in sys.argv:
        return run_server_mode()
    return run_gui_mode()


if __name__ == "__main__":
    sys.exit(main())
