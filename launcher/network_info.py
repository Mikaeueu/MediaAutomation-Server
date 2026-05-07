"""Descoberta de IP local pra exibir no launcher.

Mesmo truque do socket UDP usado pelo NetworkService do servidor, mas
duplicado aqui para que o launcher possa exibir o endereco antes mesmo
do servidor estar rodando.
"""

import socket


def get_local_ip() -> str:
    """Retorna o IP da maquina na LAN, ou ``127.0.0.1`` em caso de falha.

    Returns:
        Endereco IP como string.
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def get_hostname() -> str:
    """Retorna hostname da maquina."""
    try:
        return socket.gethostname()
    except OSError:
        return ""
