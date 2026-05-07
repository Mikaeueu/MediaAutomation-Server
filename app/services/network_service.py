"""Servico para descobrir informacoes de rede da maquina hospedeira.

Usado pela UI para exibir a URL/QR code que o celular deve acessar.
"""

import base64
import io
import re
import socket

# QR code: usamos ``segno`` (pure Python, zero dependencias transitivas).
# Caso esteja indisponivel por algum motivo, tentamos ``qrcode`` como
# fallback. Se nenhuma das duas funcionar, exibimos um placeholder.
_QR_BACKEND: str | None = None
try:
    import segno  # type: ignore
    _QR_BACKEND = "segno"
except ImportError:
    try:
        import qrcode  # type: ignore
        import qrcode.image.svg  # type: ignore
        _QR_BACKEND = "qrcode"
    except ImportError:
        _QR_BACKEND = None

from app.config import get_settings


class NetworkService:
    """Operacoes para obter informacoes de rede locais."""

    @staticmethod
    def get_local_ip() -> str:
        """Descobre o IP da maquina na LAN.

        Usa um truque clasico: cria um socket UDP e tenta "conectar" em
        um endereco externo (sem enviar nada de fato). O sistema operacional
        escolhe a interface de saida e expoe o IP correspondente.

        Returns:
            IP da interface de saida padrao, ou ``127.0.0.1`` em caso de falha.
        """
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # 8.8.8.8 nao recebe trafego algum (UDP), mas obriga o SO a
            # resolver qual interface seria usada.
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            sock.close()

    @staticmethod
    def get_hostname() -> str:
        """Retorna o hostname da maquina.

        Returns:
            Nome da maquina como string. ``""`` em caso de falha.
        """
        try:
            return socket.gethostname()
        except OSError:
            return ""

    def get_info(self) -> dict[str, str | int]:
        """Retorna um dicionario com IP, hostname e URLs de acesso.

        Inclui tambem ``mobile_qr_svg`` ja renderizado para embutir
        diretamente no HTML, sem depender de JS/CDN no cliente.

        Returns:
            Dicionario com chaves: ``ip``, ``hostname``, ``port``,
            ``desktop_url``, ``mobile_url``, ``mobile_qr_svg``.
        """
        settings = get_settings()
        ip_address = self.get_local_ip()
        port = settings.app_port
        mobile_url = f"http://{ip_address}:{port}/mobile"
        qr_svg = self.generate_qr_svg(mobile_url)
        return {
            "ip": ip_address,
            "hostname": self.get_hostname(),
            "port": port,
            "desktop_url": f"http://{ip_address}:{port}/",
            "mobile_url": mobile_url,
            "mobile_qr_svg": qr_svg,
            # Data URI prontinho pra usar em <img src=...> - mais robusto
            # que SVG inline (browser trata como imagem normal).
            "mobile_qr_data_uri": (
                "data:image/svg+xml;base64,"
                + base64.b64encode(qr_svg.encode("utf-8")).decode("ascii")
            ),
        }

    @staticmethod
    def generate_qr_svg(content: str, scale: int = 8) -> str:
        """Gera um QR code SVG inline a partir de uma string.

        Tenta primeiro ``segno`` (mais leve). Se nao estiver disponivel,
        cai pra ``qrcode``. Se nenhum estiver instalado, retorna um SVG
        placeholder em vez de quebrar a app.

        Args:
            content: Texto a ser codificado (URL, etc.).
            scale: Fator de escala do QR (tamanho dos modulos).

        Returns:
            String SVG completo (``<svg ...>...</svg>``).
        """
        if _QR_BACKEND == "segno":
            qr = segno.make(content, error="m")
            buffer = io.BytesIO()
            qr.save(buffer, kind="svg", scale=scale, border=2, xmldecl=False)
            return _normalize_qr_svg(buffer.getvalue().decode("utf-8"))

        if _QR_BACKEND == "qrcode":
            factory = qrcode.image.svg.SvgPathImage
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=scale,
                border=2,
                image_factory=factory,
            )
            qr.add_data(content)
            qr.make(fit=True)
            img = qr.make_image()
            buffer = io.BytesIO()
            img.save(buffer)
            return _normalize_qr_svg(buffer.getvalue().decode("utf-8"))

        # Fallback: nenhuma lib disponivel.
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200">'
            '<rect width="200" height="200" fill="#f1f5f9"/>'
            '<text x="100" y="95" text-anchor="middle" '
            'font-family="sans-serif" font-size="11" fill="#64748b">'
            'QR indisponivel</text>'
            '<text x="100" y="115" text-anchor="middle" '
            'font-family="sans-serif" font-size="9" fill="#94a3b8">'
            'pip install segno</text>'
            '</svg>'
        )


def _normalize_qr_svg(svg: str) -> str:
    match = re.search(r"<svg\b([^>]*)>", svg, flags=re.IGNORECASE)
    if not match:
        return svg

    attrs = match.group(1)

    # Remove width/height originais
    attrs = re.sub(r'\s+width\s*=\s*"[^"]*"', "", attrs)
    attrs = re.sub(r"\s+width\s*=\s*'[^']*'", "", attrs)
    attrs = re.sub(r'\s+height\s*=\s*"[^"]*"', "", attrs)
    attrs = re.sub(r"\s+height\s*=\s*'[^']*'", "", attrs)

    # força quadrado
    attrs += ' width="300" height="300"'

    # centralização correta
    if "preserveAspectRatio" not in attrs:
        attrs += ' preserveAspectRatio="xMidYMid meet"'

    head = svg[: match.start()]
    tail = svg[match.end():]

    return head + "<svg" + attrs + ">" + tail
