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

    A API do Holyrics usa o padrão:
        POST http://HOST:PORT/api/METHOD?token=TOKEN
    com body JSON e resposta no formato:
        {"status": "ok", "data": ...}  ou  {"status": "error", "message": "..."}
    """

    # ============================================================
    # 🔹 INIT
    # ============================================================

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        token: str | None = None,
    ):
        if host and port:
            self.host = host
            self.port = port
            self.token = token or ""
        else:
            config = load_config()
            if not config:
                raise HolyricsConnectionError("Holyrics não configurado")
            self.host = config["host"]
            self.port = config["port"]
            self.token = config.get("token", "")

        # Sem barra final — concatenamos nos métodos
        self.base_url = f"http://{self.host}:{self.port}"

    # ============================================================
    # 🔹 TESTE DE CONEXÃO (sem depender do init)
    # ============================================================

    @staticmethod
    async def test_connection(host: str, port: int, token: str) -> dict:
        """
        Testa conexão diretamente sem usar a config salva.
        Chama GetCPInfo que é o endpoint mais leve de "ping".
        """
        url = f"http://{host}:{port}/api/GetCPInfo?token={token}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(url, json={})
        except httpx.ConnectError:
            return {
                "ok": False,
                "message": f"Não foi possível conectar em {host}:{port}. "
                           "Verifique se o Holyrics está aberto e a API Server está ativada "
                           "(Holyrics > Configurações > API Server).",
            }
        except httpx.TimeoutException:
            return {
                "ok": False,
                "message": f"Timeout ao conectar em {host}:{port}. "
                           "Verifique host/porta e se o firewall permite a conexão.",
            }
        except Exception as e:
            return {"ok": False, "message": f"Erro inesperado: {e}"}

        if res.status_code == 401:
            return {"ok": False, "message": "Token inválido (HTTP 401)."}

        if res.status_code != 200:
            return {"ok": False, "message": f"HTTP {res.status_code}"}

        try:
            data = res.json()
        except Exception:
            return {"ok": False, "message": "Resposta inválida (não é JSON)."}

        if data.get("status") == "error":
            return {
                "ok": False,
                "message": data.get("message") or "Erro reportado pelo Holyrics",
            }

        return {"ok": True, "message": "Conectado com sucesso"}

    # ============================================================
    # 🔹 CORE REQUEST
    # ============================================================

    async def _post(self, method: str, body: dict | None = None) -> dict:
        """
        Faz POST na API do Holyrics.
        URL: http://HOST:PORT/api/METHOD?token=TOKEN
        """
        url = f"{self.base_url}/api/{method}?token={self.token}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                res = await client.post(url, json=body or {})
        except httpx.ConnectError as e:
            raise HolyricsConnectionError(
                f"Não foi possível conectar em {self.host}:{self.port}. "
                "Verifique se o Holyrics está rodando e a API Server está ativa."
            ) from e
        except httpx.TimeoutException as e:
            raise HolyricsConnectionError(
                f"Timeout ao conectar em {self.host}:{self.port}."
            ) from e
        except Exception as e:
            raise HolyricsConnectionError(f"Erro de conexão: {e}") from e

        if res.status_code == 401:
            raise HolyricsError("Token inválido (HTTP 401).")

        if res.status_code != 200:
            raise HolyricsError(f"HTTP {res.status_code}: {res.text[:200]}")

        try:
            data = res.json()
        except Exception as e:
            raise HolyricsError(f"Resposta inválida (não é JSON): {res.text[:200]}") from e

        if data.get("status") == "error":
            raise HolyricsError(data.get("message") or "Erro do Holyrics")

        return data

    # ============================================================
    # 🔹 AÇÕES
    # ============================================================

    async def show_verse(self, reference: str, version: str) -> dict:
        """Projeta versículo no Holyrics."""
        return await self._post("ShowVerse", {
            "references": [reference],
            "version": version,
        })

    async def close(self) -> dict:
        """Fecha projeção atual."""
        return await self._post("CloseCurrentPresentation")

    async def get_versions(self) -> list:
        """Lista versões da Bíblia disponíveis no Holyrics."""
        data = await self._post("GetBibleVersions")
        # A resposta pode ser {"status":"ok","data":["ARC","NVI",...]}
        # ou {"status":"ok","data":{"versions":[...]}} — ajuste conforme
        # o que o seu Holyrics retorna de fato.
        raw = data.get("data", [])
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict):
            return raw.get("versions", [])
        return []

    async def get_status(self) -> dict:
        """Verifica se o Holyrics está online e retorna info do CP."""
        try:
            data = await self._post("GetCPInfo")
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "message": str(e)}
