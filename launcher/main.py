"""Entry point do launcher.

Sempre roda em modo GUI - o servidor uvicorn agora roda em uma thread
no mesmo processo (via ``ServerRunner``), entao nao precisamos mais
de modo ``--server-mode`` separado.

Para rodar em desenvolvimento::

    python -m launcher.main
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


def main() -> int:
    """Inicializa Qt, MainWindow e Tray e roda o event loop."""
    os.chdir(project_root())

    # Adiciona raiz no sys.path pra import de ``app.main`` funcionar.
    root = project_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

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

    window = MainWindow(project_root=root)
    window.show()

    tray = TrayIcon(window)
    tray.show()

    return qt_app.exec()


if __name__ == "__main__":
    sys.exit(main())
