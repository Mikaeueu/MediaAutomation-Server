"""Network helpers."""

import socket
from typing import Optional


def get_local_ip(prefer_ipv4: bool = True) -> Optional[str]:
    """Return the local IP address of the host suitable for LAN access.

    The function attempts to open a UDP socket to a public IP (no data sent)
    to determine the outbound interface IP. This works without requiring
    external services.

    Args:
        prefer_ipv4: If True prefer IPv4 address.

    Returns:
        Local IP address string or None if it cannot be determined.
    """
    try:
        # Use Google's DNS as a target; no packets are actually sent.
        target = ("8.8.8.8", 80) if prefer_ipv4 else ("2001:4860:4860::8888", 80)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(target)
        ip = sock.getsockname()[0]
        sock.close()
        return ip
    except Exception:
        # Fallback: try hostname resolution
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return None
