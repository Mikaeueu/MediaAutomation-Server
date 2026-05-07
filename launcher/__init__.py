"""MediaAutomationServer Launcher.

Aplicativo desktop (PySide6) que gerencia o servidor uvicorn como subprocess
e oferece controles via janela e system tray.
"""

from launcher.version import __version__

__all__ = ["__version__"]
