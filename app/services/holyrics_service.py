import httpx
import json
import time

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
        # #region agent log
        try:
            with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H4","location":"app/services/holyrics_service.py:test_connection","message":"holyrics test connection start","data":{"host":host,"port":port,"tokenLen":len(token or "")},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
        except Exception:
            pass
        # #endregion

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
            # #region agent log
            try:
                with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H4","location":"app/services/holyrics_service.py:test_connection","message":"holyrics test unauthorized","data":{"statusCode":res.status_code},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
            except Exception:
                pass
            # #endregion
            return {"ok": False, "message": "Token inválido (HTTP 401)."}

        if res.status_code != 200:
            # #region agent log
            try:
                with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H4","location":"app/services/holyrics_service.py:test_connection","message":"holyrics test non-200","data":{"statusCode":res.status_code,"bodyPreview":res.text[:120]},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
            except Exception:
                pass
            # #endregion
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
        # #region agent log
        try:
            with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H7","location":"app/services/holyrics_service.py:_post","message":"holyrics _post request","data":{"method":method,"url":url.split('?')[0],"hasToken":bool(self.token),"bodyKeys":list((body or {}).keys())},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
        except Exception:
            pass
        # #endregion

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
            # #region agent log
            try:
                with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H7","location":"app/services/holyrics_service.py:_post","message":"holyrics _post unauthorized","data":{"method":method,"statusCode":res.status_code,"bodyPreview":res.text[:200]},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
            except Exception:
                pass
            # #endregion
            body_lower = (res.text or "").lower()
            if "unauthorized action" in body_lower:
                raise HolyricsError(
                    f"Ação não autorizada para o token na API do Holyrics ({method}). "
                    "No Holyrics > API Server > Permissões, habilite esta ação para o token."
                )
            raise HolyricsError("Token inválido (HTTP 401).")

        if res.status_code != 200:
            # #region agent log
            try:
                with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H7","location":"app/services/holyrics_service.py:_post","message":"holyrics _post non-200","data":{"method":method,"statusCode":res.status_code,"bodyPreview":res.text[:200]},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
            except Exception:
                pass
            # #endregion
            raise HolyricsError(f"HTTP {res.status_code}: {res.text[:200]}")

        try:
            data = res.json()
        except Exception as e:
            raise HolyricsError(f"Resposta inválida (não é JSON): {res.text[:200]}") from e

        if data.get("status") == "error":
            # #region agent log
            try:
                with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                    f.write(json.dumps({"sessionId":"470fcb","runId":"initial","hypothesisId":"H7","location":"app/services/holyrics_service.py:_post","message":"holyrics _post status error","data":{"method":method,"holyricsMessage":data.get("message"),"holyricsError":data.get("error"),"topKeys":list(data.keys()),"holyricsDataKeys":list((data.get("data") or {}).keys()) if isinstance(data.get("data"), dict) else []},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
            except Exception:
                pass
            # #endregion
            raise HolyricsError(data.get("message") or data.get("error") or "Erro do Holyrics")

        return data

    # ============================================================
    # 🔹 AÇÕES
    # ============================================================

    async def show_verse(self, reference: str, version: str, verse_id: str | None = None) -> dict:
        """Projeta versículo no Holyrics."""
        version_raw = (version or "").strip()
        version_lower = version_raw.lower()
        if version_lower in {"rc", "arc", "pt_arc"}:
            version_key = "pt_arc"
        else:
            version_key = version_raw

        # #region agent log
        try:
            with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"470fcb","runId":"post-fix","hypothesisId":"H15","location":"app/services/holyrics_service.py:show_verse","message":"show_verse attempt with verse id first","data":{"reference":reference,"verseId":verse_id,"versionInput":version_raw,"versionKey":version_key},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
        except Exception:
            pass
        # #endregion
        if verse_id:
            try:
                return await self._post("ShowVerse", {
                    "id": verse_id,
                    "version": version_key,
                })
            except HolyricsError as e:
                # #region agent log
                try:
                    with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                        f.write(json.dumps({"sessionId":"470fcb","runId":"post-fix","hypothesisId":"H15","location":"app/services/holyrics_service.py:show_verse","message":"show_verse id attempt failed; trying reference fallback","data":{"error":str(e),"verseId":verse_id},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
                except Exception:
                    pass
                # #endregion
                if "item not found" not in str(e).lower():
                    raise

        return await self._post("ShowVerse", {
            "references": reference,
            "version": version_key,
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
        versions = []
        if isinstance(raw, list):
            versions = raw
        elif isinstance(raw, dict):
            versions = raw.get("versions", [])
        # #region agent log
        try:
            with open("debug-470fcb.log", "a", encoding="utf-8") as f:
                f.write(json.dumps({"sessionId":"470fcb","runId":"post-fix","hypothesisId":"H11","location":"app/services/holyrics_service.py:get_versions","message":"holyrics versions resolved","data":{"count":len(versions or []),"sample":(versions or [])[:10]},"timestamp":int(time.time()*1000)}, ensure_ascii=True) + "\n")
        except Exception:
            pass
        # #endregion
        return versions

    async def action_next(self) -> dict:
        """Avanca pro proximo slide da projecao atual (leve, nao reprojeta)."""
        return await self._post("ActionNext")

    async def action_previous(self) -> dict:
        """Volta pro slide anterior da projecao atual (leve, nao reprojeta)."""
        return await self._post("ActionPrevious")

    async def action_go_to_index(self, index: int) -> dict:
        """Pula direto pra um slide especifico (leve, nao reprojeta)."""
        return await self._post("ActionGoToIndex", {"index": int(index)})

    async def get_chapter_verses(
        self, version: str, book: str, chapter: int
    ) -> list[dict]:
        """Tenta buscar texto de todos os versiculos de um capitulo.

        A API do Holyrics nao expoe um endpoint padronizado pra ler
        Biblia (so projetar). Tentamos varios nomes/payloads conhecidos
        e fazemos fallback graceful: se nada funcionar, retorna lista
        vazia (a UI cai pra modo "so numeros").

        Returns:
            Lista de ``{"verse": int, "text": str}``. ``text`` pode
            estar vazio se a API nao retornou.
        """
        version_raw = (version or "").strip()
        version_lower = version_raw.lower()
        if version_lower in {"rc", "arc", "pt_arc"}:
            version_key = "pt_arc"
        else:
            version_key = version_raw

        attempts = [
            ("GetBibleVerses", {"version": version_key, "book": book, "chapter": chapter}),
            ("GetBibleChapter", {"version": version_key, "book": book, "chapter": chapter}),
            ("GetVerse", {"version": version_key, "book": book, "chapter": chapter}),
        ]
        for method, payload in attempts:
            try:
                resp = await self._post(method, payload)
                raw = resp.get("data") or resp.get("verses") or []
                verses: list[dict] = []
                if isinstance(raw, list):
                    for i, item in enumerate(raw, start=1):
                        if isinstance(item, str):
                            verses.append({"verse": i, "text": item})
                        elif isinstance(item, dict):
                            verses.append({
                                "verse": int(item.get("verse") or item.get("number") or i),
                                "text": item.get("text") or item.get("content") or "",
                            })
                if verses:
                    return verses
            except HolyricsError:
                continue
            except Exception:
                continue
        return []

    async def get_status(self) -> dict:
        """Verifica se o Holyrics está online e retorna info do CP."""
        try:
            data = await self._post("GetCPInfo")
            return {"ok": True, "data": data}
        except Exception as e:
            return {"ok": False, "message": str(e)}
