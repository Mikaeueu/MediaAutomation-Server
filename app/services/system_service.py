"""Servico que executa acoes do sistema operacional (desligar, suspender).

Toda chamada a ``subprocess`` fica encapsulada aqui para facilitar mock em
testes e centralizar comandos especificos do Windows.
"""

import subprocess
import sys


class SystemService:
    """Comandos do SO: shutdown e suspend."""

    @staticmethod
    def is_windows() -> bool:
        """Retorna True quando rodando em Windows."""
        return sys.platform.startswith("win")

    def shutdown_now(self) -> None:
        """Executa o desligamento imediato do PC.

        No Windows usa ``shutdown /s /f /t 0``. Em outros SOs (testes em
        Linux) usa ``shutdown -h now`` quando disponivel.
        """
        if self.is_windows():
            subprocess.Popen(
                ["shutdown", "/s", "/f", "/t", "0"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            subprocess.Popen(["shutdown", "-h", "now"])

    def suspend_now(self) -> None:
        """Executa a suspensao imediata do PC.

        No Windows: ``rundll32.exe powrprof.dll,SetSuspendState 0,1,0``.
        Importante: a hibernacao deve estar desabilitada para suspender
        de fato (caso contrario o comando hiberna). O usuario pode
        desabilitar com ``powercfg -h off`` em prompt admin.
        """
        if self.is_windows():
            subprocess.Popen(
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            subprocess.Popen(["systemctl", "suspend"])

    def cancel_pending_shutdown(self) -> None:
        """Cancela um ``shutdown /s`` previamente disparado pelo proprio Windows.

        Util quando alguem agenda via ``shutdown /s /t N`` por engano. O
        agendamento da nossa app nao usa esse mecanismo, mas e bom expor
        a opcao caso o usuario tenha disparado manualmente.
        """
        if self.is_windows():
            subprocess.Popen(
                ["shutdown", "/a"],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

    def execute(self, action: str) -> None:
        """Despacha uma acao por nome.

        Args:
            action: ``"shutdown"`` ou ``"suspend"``.

        Raises:
            ValueError: Se ``action`` nao for reconhecida.
        """
        if action == "shutdown":
            self.shutdown_now()
        elif action == "suspend":
            self.suspend_now()
        else:
            raise ValueError(f"Acao invalida: {action!r}")
