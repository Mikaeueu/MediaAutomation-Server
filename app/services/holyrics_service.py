import httpx

from app.core.holyrics_store import load_config


class HolyricsError(Exception):
    """Erro genérico da API do Holyrics."""
    pass


class HolyricsConnectionError(Exception):
    """Erro de conexão com o Holyrics."""
    pass


class HolyricsService:
    """
    Cliente para comunicação com a API local do Holyrics.
    """

    # ============================================================
    # 🔹 INIT
    # ============================================================

    def __init__(self, host: str | None = None, port: int | None = None, token: str | None = None):
        """
        Se não passar parâmetros, usa config salva automaticamente.
        """

        if host and port:
            # 🔹 Usa dados informados (ex: teste)
            self.host = host
            self.port = port
            self.token = token or ""

        else:
            # 🔹 Usa config salva
            config = load_config()

            if not config:
                raise HolyricsConnectionError("Holyrics não configurado")

            self.host = config["host"]
            self.port = config["port"]
            self.token = config.get("token", "")

        self.base_url = f"http://{self.host}:{self.port}/api"

    # ============================================================
    # 🔹 TESTE DE CONEXÃO (SEM DEPENDER DE INIT)
    # ============================================================

    @staticmethod
    async def test_connection(host: str, port: int, token: str) -> dict:
        """
        Testa conexão sem depender da config salva.
        """

        base_url = f"http://{host}:{port}/api"
        url = f"{base_url}/GetCPInfo?token={token}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(url, json={})

        except Exception as e:
            return {
                "ok": False,
                "message": f"Erro de conexão: {e}",
            }

        if res.status_code != 200:
            return {
                "ok": False,
                "message": f"HTTP {res.status_code}",
            }

        data = res.json()

        if data.get("status") == "error":
            return {
                "ok": False,
                "message": data.get("message") or "Erro do Holyrics",
            }

        return {
            "ok": True,
            "message": "Conectado com sucesso",
        }

    # ============================================================
    # 🔹 CORE REQUEST
    # ============================================================

    async def _post(self, method: str, body: dict | None = None) -> dict:
        """Faz POST na API do Holyrics."""

        url = f"{self.base_url}/{method}?token={self.token}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(url, json=body or {})

        except Exception as e:
            raise HolyricsConnectionError(f"Erro de conexão: {e}")

        if res.status_code != 200:
            raise HolyricsError(f"HTTP {res.status_code}: {res.text}")

        data = res.json()

        if data.get("status") == "error":
            raise HolyricsError(data.get("message") or "Erro do Holyrics")

        return data

    # ============================================================
    # 🔹 AÇÕES
    # ============================================================

    async def show_verse(self, reference: str, version: str) -> dict:
        """Projeta versículo."""
        return await self._post("ShowVerse", {
            "references": [reference],
            "version": version,
        })

    async def close(self) -> dict:
        """Fecha projeção."""
        return await self._post("CloseCurrentPresentation")

    async def get_versions(self) -> list:
        """Lista versões da Bíblia."""
        data = await self._post("GetBibleVersions")
        return data.get("data", [])

    async def get_status(self) -> dict:
        """Verifica se o Holyrics está online."""
        try:
            data = await self._post("GetCPInfo")

            return {
                "ok": True,
                "data": data,
            }

        except Exception as e:
            return {
                "ok": False,
                "message": str(e),
            }