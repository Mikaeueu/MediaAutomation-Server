"""Janela principal do launcher (PySide6).

Layout: header com logo + versao, indicador de status, botao iniciar/parar,
caixa de enderecos, botoes secundarios (abrir navegador, ver log,
verificar update), checkbox de autostart.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from pathlib import Path

from PySide6.QtCore import QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from launcher import autostart
from launcher.network_info import get_local_ip
from launcher.server_runner import ServerRunner
from launcher.version import __version__


# Paleta inspirada no painel web (slate-950 + brand-500).
QSS = """
QMainWindow, QDialog { background-color: #0f172a; }
QLabel { color: #e2e8f0; }
QLabel#title { font-size: 16pt; font-weight: 600; color: #f8fafc; }
QLabel#muted { color: #94a3b8; font-size: 9pt; }
QLabel#status { font-size: 11pt; font-weight: 500; }
QLabel#address { color: #cbd5e1; font-family: Consolas, monospace; font-size: 9pt; }
QPushButton {
    background-color: #1e293b;
    color: #e2e8f0;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 14px;
    font-size: 9pt;
}
QPushButton:hover { background-color: #334155; border-color: #475569; }
QPushButton:disabled { background-color: #1e293b; color: #64748b; }
QPushButton#primary {
    background-color: #4f6df5;
    color: white;
    border: none;
    font-weight: 600;
    font-size: 11pt;
    padding: 14px;
    border-radius: 10px;
}
QPushButton#primary:hover { background-color: #3d54d4; }
QPushButton#primary:disabled { background-color: #334155; color: #64748b; }
QPushButton#stop {
    background-color: #ef4444;
    color: white;
    border: none;
    font-weight: 600;
    font-size: 11pt;
    padding: 14px;
    border-radius: 10px;
}
QPushButton#stop:hover { background-color: #dc2626; }
QCheckBox { color: #cbd5e1; font-size: 9pt; }
QPlainTextEdit {
    background-color: #020617;
    color: #cbd5e1;
    border: 1px solid #1e293b;
    border-radius: 6px;
    font-family: Consolas, monospace;
    font-size: 9pt;
}
"""


def make_app_icon(size: int = 64) -> QIcon:
    """Cria um QIcon programaticamente (sem precisar de arquivo).

    Quadrado azul com gradiente sutil simulando o logo do painel.

    Args:
        size: Lado do icone em pixels.

    Returns:
        QIcon pronto para uso em janela e tray.
    """
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    painter = QPainter(pm)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#4f6df5"))
    painter.setPen(Qt.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size * 0.22, size * 0.22)
    # Triangulo branco simulando "play" no centro.
    painter.setBrush(QColor("#ffffff"))
    side = size * 0.42
    cx = size / 2
    cy = size / 2
    points = [
        (cx - side / 2, cy - side / 2),
        (cx - side / 2, cy + side / 2),
        (cx + side / 2, cy),
    ]
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QPolygonF
    poly = QPolygonF([QPointF(x, y) for x, y in points])
    painter.drawPolygon(poly)
    painter.end()
    return QIcon(pm)


class LogDialog(QDialog):
    """Janela secundaria mostrando log do servidor em tempo real."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Inicializa a janela de log."""
        super().__init__(parent)
        self.setWindowTitle("Log do servidor")
        self.resize(720, 480)
        layout = QVBoxLayout(self)
        self._text = QPlainTextEdit(self)
        self._text.setReadOnly(True)
        layout.addWidget(self._text)

    def append(self, line: str) -> None:
        """Adiciona uma linha ao log."""
        self._text.appendPlainText(line)


class MainWindow(QMainWindow):
    """Janela principal do launcher."""

    request_quit = Signal()  # sinal pro tray usar quando fechar de verdade

    def __init__(self, project_root: Path) -> None:
        """Inicializa a janela e configura o ServerRunner."""
        super().__init__()
        self.setWindowTitle("MediaAutomationServer")
        self.setFixedSize(QSize(520, 460))
        self.setStyleSheet(QSS)
        self.setWindowIcon(make_app_icon(64))

        self._project_root = project_root
        self._runner = ServerRunner(project_root=project_root)
        self._runner.set_log_handler(self._on_log)
        self._runner.set_state_handler(self._on_state_change)
        self._log_dialog = LogDialog(self)

        self._build_ui()
        self._refresh_addresses()
        self._refresh_status_label()

        # Pequeno polling pra manter labels sincronizados.
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status_label)
        self._timer.start(1000)

    # ---------------------- Construcao da UI ----------------------

    def _build_ui(self) -> None:
        """Constroi a hierarquia de widgets."""
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        # Header: logo + nome + versao
        header = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(make_app_icon(48).pixmap(48, 48))
        header.addWidget(logo)
        title_box = QVBoxLayout()
        title_box.setSpacing(0)
        title = QLabel("MediaAutomationServer")
        title.setObjectName("title")
        version_lbl = QLabel(f"versao {__version__}")
        version_lbl.setObjectName("muted")
        title_box.addWidget(title)
        title_box.addWidget(version_lbl)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        # Status
        status_row = QHBoxLayout()
        self._status_dot = QLabel("●")
        self._status_dot.setStyleSheet("color: #ef4444; font-size: 14pt;")
        self._status_label = QLabel("Servidor parado")
        self._status_label.setObjectName("status")
        status_row.addWidget(self._status_dot)
        status_row.addWidget(self._status_label)
        status_row.addStretch(1)
        layout.addLayout(status_row)

        # Botao primario start/stop
        self._main_button = QPushButton("Iniciar servidor")
        self._main_button.setObjectName("primary")
        self._main_button.clicked.connect(self._toggle_server)
        layout.addWidget(self._main_button)

        # Enderecos
        addr_label = QLabel("Enderecos:")
        addr_label.setObjectName("muted")
        layout.addWidget(addr_label)
        self._desktop_addr = QLabel()
        self._desktop_addr.setObjectName("address")
        self._desktop_addr.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._mobile_addr = QLabel()
        self._mobile_addr.setObjectName("address")
        self._mobile_addr.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self._desktop_addr)
        layout.addWidget(self._mobile_addr)

        # Botoes secundarios
        actions = QHBoxLayout()
        self._open_browser_btn = QPushButton("Abrir no navegador")
        self._open_browser_btn.clicked.connect(self._open_browser)
        self._log_btn = QPushButton("Ver log")
        self._log_btn.clicked.connect(self._show_log)
        self._update_btn = QPushButton("Verificar atualizacao")
        self._update_btn.clicked.connect(self._check_update)
        self._update_btn.setToolTip("Consulta o Supabase pela versao mais recente")
        actions.addWidget(self._open_browser_btn)
        actions.addWidget(self._log_btn)
        actions.addWidget(self._update_btn)
        layout.addLayout(actions)

        # Botao pra editar credenciais de login do painel web.
        self._login_btn = QPushButton("Login do painel")
        self._login_btn.setToolTip(
            "Editar usuario e senha pra acessar o painel web no navegador"
        )
        self._login_btn.clicked.connect(self._edit_login)
        layout.addWidget(self._login_btn)

        layout.addStretch(1)

        # Footer: autostart
        footer = QHBoxLayout()
        self._autostart_cb = QCheckBox("Iniciar com o Windows")
        self._autostart_cb.setChecked(autostart.is_enabled())
        self._autostart_cb.toggled.connect(self._toggle_autostart)
        footer.addWidget(self._autostart_cb)
        footer.addStretch(1)
        layout.addLayout(footer)

    # ---------------------- Acoes ----------------------

    def _toggle_server(self) -> None:
        """Alterna entre iniciar e parar o servidor."""
        if self._runner.is_running:
            self._runner.stop()
        else:
            self._runner.start()

    def _open_browser(self) -> None:
        """Abre o painel desktop no navegador."""
        webbrowser.open(f"http://localhost:{self._runner.port}/")

    def _show_log(self) -> None:
        """Mostra a janela de log."""
        self._log_dialog.show()
        self._log_dialog.raise_()
        self._log_dialog.activateWindow()

    def _check_update(self) -> None:
        """Verifica se ha versao mais nova no Supabase e oferece download."""
        from PySide6.QtWidgets import QMessageBox  # noqa: PLC0415

        from launcher import updater  # noqa: PLC0415

        self._update_btn.setEnabled(False)
        try:
            latest = updater.check_for_updates()
        except updater.UpdateError as exc:
            QMessageBox.warning(self, "Atualizacao", str(exc))
            return
        finally:
            self._update_btn.setEnabled(True)

        if latest is None:
            QMessageBox.information(
                self,
                "Atualizacao",
                "Voce ja esta na versao mais recente.",
            )
            return

        notes = latest.get("release_notes") or "(sem notas de versao)"
        msg = QMessageBox(self)
        msg.setWindowTitle("Atualizacao disponivel")
        msg.setIcon(QMessageBox.Information)
        msg.setText(f"Versao {latest.get('version')} disponivel.")
        msg.setInformativeText(
            f"Notas:\n{notes}\n\nAbrir a pagina de download no navegador?"
        )
        msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        if msg.exec() != QMessageBox.Yes:
            return

        # Abre o link de share do Drive direto no navegador. Mais confiavel
        # que baixar via API do Drive (que bloqueia arquivos > 100MB e exige
        # confirmacao). User clica em "Download" no Drive e instala.
        download_url = latest.get("download_url", "")
        if not download_url:
            QMessageBox.warning(self, "Link ausente", "URL de download vazia.")
            return
        import webbrowser  # noqa: PLC0415
        webbrowser.open(download_url)
        QMessageBox.information(
            self,
            "Download",
            "A pagina foi aberta no navegador. Baixe o instalador, feche este "
            "app e execute o arquivo baixado pra atualizar.",
        )

    def _edit_login(self) -> None:
        """Abre dialogo pra editar usuario e senha do painel web.

        Le o usuario atual do banco SQLite (mesmo que o servidor usa) e
        ao salvar substitui as credenciais. O servidor nao precisa estar
        rodando - editamos o banco diretamente via UserRepository.
        """
        from PySide6.QtWidgets import (  # noqa: PLC0415
            QDialog, QDialogButtonBox, QFormLayout, QLineEdit, QMessageBox,
        )

        # Le usuario atual (cria default 'midiadm' se nao tiver).
        try:
            from app.core.security import hash_password  # noqa: PLC0415
            from app.database import init_database  # noqa: PLC0415
            from app.models.user import User  # noqa: PLC0415
            from app.repositories.user_repository import UserRepository  # noqa: PLC0415
            init_database()
            repo = UserRepository()
            users = repo.list_all()
            current_user = users[0].username if users else "midiadm"
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Falha ao ler credenciais: {exc}")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Login do painel")
        dlg.setMinimumWidth(360)
        form = QFormLayout(dlg)

        user_input = QLineEdit(current_user)
        pass_input = QLineEdit()
        pass_input.setPlaceholderText("(deixe em branco pra manter senha atual)")
        pass_input.setEchoMode(QLineEdit.Password)
        show_pass = QLineEdit()
        show_cb_text = "Mostrar senha"
        from PySide6.QtWidgets import QCheckBox  # noqa: PLC0415
        show_cb = QCheckBox(show_cb_text)
        show_cb.toggled.connect(
            lambda checked: pass_input.setEchoMode(
                QLineEdit.Normal if checked else QLineEdit.Password
            )
        )

        form.addRow("Usuario:", user_input)
        form.addRow("Nova senha:", pass_input)
        form.addRow("", show_cb)

        buttons = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        form.addRow(buttons)

        if dlg.exec() != QDialog.Accepted:
            return

        new_user = user_input.text().strip().lower()
        new_pass = pass_input.text()
        if not new_user:
            QMessageBox.warning(self, "Login", "Usuario nao pode ser vazio.")
            return

        try:
            # Pega senha atual se vazio.
            if not new_pass:
                if not users:
                    QMessageBox.warning(
                        self, "Login", "Defina uma senha (banco vazio)."
                    )
                    return
                new_hash = users[0].password_hash
            else:
                new_hash = hash_password(new_pass)

            # Apaga todos e cria 1 novo (mais simples que update inteligente).
            for u in repo.list_all():
                repo.delete(u.id)
            repo.create(User(username=new_user, password_hash=new_hash))
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Erro", f"Falha ao salvar: {exc}")
            return

        QMessageBox.information(
            self,
            "Login atualizado",
            f"Login do painel atualizado para '{new_user}'.\n\n"
            "Se o painel ja estiver aberto no navegador, faca logout e "
            "entre novamente.",
        )

    def _toggle_autostart(self, enabled: bool) -> None:
        """Liga ou desliga o autostart no registro do Windows."""
        exe = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
        if enabled:
            autostart.enable(exe)
        else:
            autostart.disable()

    # ---------------------- Atualizacao da UI ----------------------

    def _refresh_addresses(self) -> None:
        """Recalcula e exibe enderecos local e LAN."""
        ip = get_local_ip()
        port = self._runner.port
        self._desktop_addr.setText(f"  Desktop:  http://localhost:{port}/")
        self._mobile_addr.setText(f"  Mobile:   http://{ip}:{port}/mobile")

    def _refresh_status_label(self) -> None:
        """Atualiza ponto + texto baseado no estado do runner."""
        state = self._runner.state
        mapping = {
            ServerRunner.STATE_STOPPED: ("Servidor parado", "#ef4444"),
            ServerRunner.STATE_STARTING: ("Iniciando...", "#f59e0b"),
            ServerRunner.STATE_RUNNING: ("Servidor rodando", "#10b981"),
            ServerRunner.STATE_STOPPING: ("Parando...", "#f59e0b"),
            ServerRunner.STATE_ERROR: ("Erro ao iniciar", "#ef4444"),
        }
        text, color = mapping.get(state, ("?", "#94a3b8"))
        self._status_label.setText(text)
        self._status_dot.setStyleSheet(f"color: {color}; font-size: 14pt;")
        self._main_button.setText(
            "Parar servidor" if self._runner.is_running else "Iniciar servidor"
        )
        self._main_button.setObjectName(
            "stop" if self._runner.is_running else "primary"
        )
        # Re-aplica stylesheet apos trocar objectName.
        self._main_button.style().unpolish(self._main_button)
        self._main_button.style().polish(self._main_button)
        self._open_browser_btn.setEnabled(self._runner.is_running)

    # ---------------------- Callbacks do runner ----------------------

    def _on_log(self, line: str) -> None:
        """Adiciona linha ao log dialog (executa no thread do reader)."""
        # Como pode vir de outra thread, usamos invokeMethod via signal seria
        # mais correto, mas QPlainTextEdit.appendPlainText e thread-safe na
        # pratica do PySide6 quando chamado pelo event loop. Vou usar QTimer
        # singleShot pra agendar no main thread.
        QTimer.singleShot(0, lambda: self._log_dialog.append(line))

    def _on_state_change(self, new_state: str) -> None:
        """Re-renderiza quando o runner muda de estado."""
        QTimer.singleShot(0, self._refresh_status_label)

    # ---------------------- Lifecycle ----------------------

    def closeEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        """Quando fecha a janela, esconde em vez de matar (segue no tray)."""
        event.ignore()
        self.hide()

    def really_quit(self) -> None:
        """Encerra o servidor e a app de verdade (chamado pelo tray)."""
        self._runner.stop()
        QApplication.quit()
