"""System tray icon do launcher."""

from __future__ import annotations

import webbrowser

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QSystemTrayIcon

from launcher.main_window import MainWindow, make_app_icon


class TrayIcon(QSystemTrayIcon):
    """Icone na bandeja com menu contextual."""

    def __init__(self, window: MainWindow) -> None:
        """Inicializa o tray e conecta acoes.

        Args:
            window: Janela principal a controlar.
        """
        super().__init__(make_app_icon(64))
        self._window = window
        self.setToolTip("MediaAutomationServer")

        menu = QMenu()
        show_action = QAction("Abrir painel", menu)
        show_action.triggered.connect(self._show_window)
        menu.addAction(show_action)

        browser_action = QAction("Abrir no navegador", menu)
        browser_action.triggered.connect(self._open_browser)
        menu.addAction(browser_action)

        menu.addSeparator()

        self._toggle_action = QAction("Iniciar servidor", menu)
        self._toggle_action.triggered.connect(window._toggle_server)
        menu.addAction(self._toggle_action)

        menu.addSeparator()

        quit_action = QAction("Sair", menu)
        quit_action.triggered.connect(window.really_quit)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        self.activated.connect(self._on_activated)

        # Atualiza texto do toggle conforme estado.
        window._runner.set_state_handler(self._refresh_toggle_label)

    def _show_window(self) -> None:
        """Mostra e foca a janela principal."""
        self._window.show()
        self._window.raise_()
        self._window.activateWindow()

    def _open_browser(self) -> None:
        """Abre o painel no navegador padrao."""
        webbrowser.open(f"http://localhost:{self._window._runner.port}/")

    def _on_activated(self, reason) -> None:
        """Click duplo no tray abre a janela."""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_window()

    def _refresh_toggle_label(self, state: str) -> None:
        """Mantem o texto do menu consistente com o estado do servidor."""
        running = state in ("running", "starting")
        self._toggle_action.setText(
            "Parar servidor" if running else "Iniciar servidor"
        )
