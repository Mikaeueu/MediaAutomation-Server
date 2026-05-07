"""Servico async para falar com o OBS via WebSocket v5 (simpleobsws).

Singleton com:
  * conexao lazy (so conecta quando necessario);
  * reconexao automatica em caso de queda;
  * lock para evitar concorrencia em operacoes de conexao.

A camada de routers (``app.routers.obs``) nunca lida com simpleobsws
direto — sempre via os metodos de alto nivel deste servico.
"""

import asyncio
import contextlib
from typing import Any

try:
    import simpleobsws  # type: ignore
    _OBS_LIB_AVAILABLE = True
except ImportError:
    _OBS_LIB_AVAILABLE = False

from app.repositories.hidden_scenes_repository import HiddenScenesRepository
from app.repositories.obs_config_repository import ObsConfigRepository


class OBSConnectionError(Exception):
    """Lancada quando a conexao ou request com o OBS falha."""


class OBSService:
    """Singleton async que mantem a conexao com o OBS WebSocket."""

    _instance: "OBSService | None" = None

    def __new__(cls) -> "OBSService":
        """Garante uma unica instancia por processo (singleton)."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
            cls._instance._lock = asyncio.Lock()
            cls._instance._last_error: str | None = None
            cls._instance._repo = ObsConfigRepository()
        return cls._instance

    # ---------------------- Conexao ----------------------

    @property
    def is_connected(self) -> bool:
        """Indica se ha um client identificado e ativo no momento."""
        return bool(self._client and getattr(self._client, "ws", None))

    async def _connect(self) -> None:
        """Cria um client novo a partir da config atual e identifica."""
        if not _OBS_LIB_AVAILABLE:
            raise OBSConnectionError(
                "Lib simpleobsws nao instalada. Rode 'pip install simpleobsws'."
            )

        # Garante que nenhum client antigo fique pendurado (sessoes fantasmas).
        if self._client is not None:
            try:
                await self._client.disconnect()
            except Exception:  # noqa: BLE001
                pass
            self._client = None

        config = self._repo.get()
        url = f"ws://{config.host}:{config.port}"
        password = (config.password or "").strip() or None

        params = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False,
            eventSubscriptions=0,  # nao precisamos receber eventos
        )
        client = simpleobsws.WebSocketClient(
            url=url,
            password=password,
            identification_parameters=params,
        )
        try:
            await client.connect()
        except OSError as exc:
            raise OBSConnectionError(
                f"Nao foi possivel conectar em {url}: {exc}"
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise OBSConnectionError(
                f"Falha ao conectar em {url}: {type(exc).__name__}: {exc}"
            ) from exc

        # Timeout maior + log detalhado em caso de falha de identify.
        try:
            ok = await client.wait_until_identified(timeout=20)
        except Exception as exc:  # noqa: BLE001
            with contextlib.suppress(Exception):
                await client.disconnect()
            raise OBSConnectionError(
                f"Erro durante identify: {type(exc).__name__}: {exc}"
            ) from exc

        if not ok:
            with contextlib.suppress(Exception):
                await client.disconnect()
            raise OBSConnectionError(
                "OBS aceitou a conexao mas o handshake de identificacao "
                "falhou. Verifique: (1) versao do OBS WebSocket >= 5.0; "
                "(2) senha exatamente igual a do OBS (sem espacos extras); "
                "(3) se 'Habilitar autenticacao' esta marcado e bate com o "
                "campo senha aqui. Se senha nao tem auth, deixe em branco."
            )

        self._client = client
        self._last_error = None

    async def ensure_connected(self) -> None:
        """Garante que ha uma conexao ativa, reconectando se necessario."""
        async with self._lock:
            if self.is_connected:
                return
            await self._connect()

    async def disconnect(self) -> None:
        """Desconecta gracioso, limpando o client cacheado."""
        async with self._lock:
            if self._client is not None:
                try:
                    await self._client.disconnect()
                except Exception:  # noqa: BLE001
                    pass
                self._client = None

    async def reconnect(self) -> None:
        """Forca uma reconexao (drop + connect)."""
        await self.disconnect()
        await self.ensure_connected()

    # ---------------------- Request generico ----------------------

    async def call(self, request_type: str, data: dict | None = None) -> dict:
        """Executa um request OBS WebSocket e retorna ``responseData``.

        Args:
            request_type: Nome do request (ex: ``GetSceneList``).
            data: Parametros do request, se houver.

        Returns:
            Dicionario com ``responseData`` (ou ``{}`` se vazio).

        Raises:
            OBSConnectionError: Se nao conseguir conectar ou se o OBS retornar erro.
        """
        try:
            await self.ensure_connected()
        except OBSConnectionError:
            raise
        try:
            request = simpleobsws.Request(request_type, data or {})
            response = await self._client.call(request)
            if not response.ok():
                raise OBSConnectionError(
                    f"OBS rejeitou {request_type}: {response.requestStatus.comment}"
                )
            return response.responseData or {}
        except Exception as exc:  # noqa: BLE001
            self._last_error = str(exc)
            # Drop client em qualquer falha pra forçar reconnect na proxima.
            self._client = None
            if isinstance(exc, OBSConnectionError):
                raise
            raise OBSConnectionError(str(exc)) from exc

    # ---------------------- API publica de alto nivel ----------------------

    async def get_status(self) -> dict[str, Any]:
        """Retorna status geral: conectado, versao, cena, gravacao."""
        if not _OBS_LIB_AVAILABLE:
            return {
                "connected": False,
                "error": "simpleobsws nao instalado",
                "last_error": self._last_error,
            }
        try:
            version = await self.call("GetVersion")
            scene = await self.call("GetCurrentProgramScene")
            recording = await self.call("GetRecordStatus")
            return {
                "connected": True,
                "obs_version": version.get("obsVersion"),
                "websocket_version": version.get("obsWebSocketVersion"),
                "current_scene": scene.get("currentProgramSceneName"),
                "recording": {
                    "active": bool(recording.get("outputActive")),
                    "paused": bool(recording.get("outputPaused")),
                    "duration_ms": recording.get("outputDuration", 0),
                    "timecode": recording.get("outputTimecode", "00:00:00"),
                },
                "last_error": None,
            }
        except OBSConnectionError as exc:
            return {
                "connected": False,
                "error": str(exc),
                "last_error": str(exc),
            }

    async def list_scenes(self) -> dict[str, Any]:
        """Retorna todas as cenas com flag de ocultas e ordenadas.

        Cenas visiveis vem primeiro (na ordem original do OBS); cenas
        marcadas como ocultas (em ``obs_hidden_scenes``) vao pro fim,
        com flag ``hidden=True`` pra UI tratar diferente.
        """
        data = await self.call("GetSceneList")
        raw = data.get("scenes", [])
        # OBS retorna cenas em ordem reversa (ultima criada primeiro).
        ordered = sorted(raw, key=lambda s: s["sceneIndex"])

        hidden_set = HiddenScenesRepository().list_set()
        visible: list[dict] = []
        hidden: list[dict] = []
        for scene in ordered:
            entry = {
                "name": scene["sceneName"],
                "index": scene["sceneIndex"],
                "hidden": scene["sceneName"] in hidden_set,
            }
            (hidden if entry["hidden"] else visible).append(entry)

        return {
            "current": data.get("currentProgramSceneName"),
            "scenes": visible + hidden,  # ocultas no fim
        }

    async def switch_scene(self, scene_name: str) -> None:
        """Troca a cena ativa do programa."""
        await self.call("SetCurrentProgramScene", {"sceneName": scene_name})

    async def list_scene_collections(self) -> dict[str, Any]:
        """Retorna todas as scene collections cadastradas."""
        data = await self.call("GetSceneCollectionList")
        return {
            "current": data.get("currentSceneCollectionName"),
            "collections": data.get("sceneCollections", []),
        }

    async def switch_scene_collection(self, name: str) -> None:
        """Troca para uma scene collection.

        OBS reabre/recarrega tudo ao trocar de collection - a conexao pode
        cair temporariamente. Forcamos reconexao apos a chamada.
        """
        await self.call("SetCurrentSceneCollection", {"sceneCollectionName": name})
        # Aguarda OBS estabilizar e reconecta.
        await asyncio.sleep(0.5)
        await self.disconnect()

    async def start_recording(self) -> None:
        """Inicia a gravacao (idempotente: se ja esta gravando, nao falha)."""
        status = await self.call("GetRecordStatus")
        if status.get("outputActive"):
            return
        await self.call("StartRecord")

    async def stop_recording(self) -> dict[str, Any]:
        """Para a gravacao.

        Returns:
            Dicionario com ``outputPath`` (caminho do arquivo gravado), se houver.
        """
        status = await self.call("GetRecordStatus")
        if not status.get("outputActive"):
            return {"outputPath": None, "wasActive": False}
        result = await self.call("StopRecord")
        return {"outputPath": result.get("outputPath"), "wasActive": True}

    async def toggle_recording(self) -> dict[str, Any]:
        """Alterna entre iniciar e parar gravacao baseado no estado atual."""
        status = await self.call("GetRecordStatus")
        if status.get("outputActive"):
            return {"action": "stopped", **(await self.stop_recording())}
        await self.start_recording()
        return {"action": "started"}

    # ---------------------- Modos / janelas ----------------------

    async def get_studio_mode(self) -> bool:
        """Retorna se o Studio Mode esta ativo."""
        data = await self.call("GetStudioModeEnabled")
        return bool(data.get("studioModeEnabled"))

    async def set_studio_mode(self, enabled: bool) -> bool:
        """Liga ou desliga o Studio Mode. Retorna o novo estado."""
        await self.call("SetStudioModeEnabled", {"studioModeEnabled": enabled})
        return enabled

    async def get_virtual_cam(self) -> bool:
        """Retorna se a Camera Virtual esta ativa."""
        data = await self.call("GetVirtualCamStatus")
        return bool(data.get("outputActive"))

    async def toggle_virtual_cam(self) -> bool:
        """Alterna a Camera Virtual. Retorna o novo estado (ativa/inativa)."""
        data = await self.call("ToggleVirtualCam")
        return bool(data.get("outputActive"))

    async def get_replay_buffer(self) -> bool:
        """Retorna se o Replay Buffer esta ativo."""
        data = await self.call("GetReplayBufferStatus")
        return bool(data.get("outputActive"))

    async def toggle_replay_buffer(self) -> bool:
        """Alterna o Replay Buffer. Retorna o novo estado."""
        data = await self.call("ToggleReplayBuffer")
        return bool(data.get("outputActive"))

    # ---------------------- Audio ----------------------

    async def list_audio_inputs(self) -> list[dict[str, Any]]:
        """Lista inputs com audio + volume + mute.

        Tenta pegar volume de cada input; os que nao tem audio sao
        descartados silenciosamente (OBS retorna erro pra esses).

        Returns:
            Lista de dicts com keys: ``name``, ``volume_mul``, ``volume_db``,
            ``muted``.
        """
        data = await self.call("GetInputList")
        inputs = data.get("inputs", [])
        result: list[dict[str, Any]] = []
        for inp in inputs:
            name = inp.get("inputName")
            if not name:
                continue
            try:
                volume = await self.call("GetInputVolume", {"inputName": name})
                mute = await self.call("GetInputMute", {"inputName": name})
                result.append({
                    "name": name,
                    "volume_mul": volume.get("inputVolumeMul", 1.0),
                    "volume_db": volume.get("inputVolumeDb", 0.0),
                    "muted": bool(mute.get("inputMuted")),
                })
            except OBSConnectionError:
                # Input sem audio - ignora.
                continue
        return result

    async def set_input_volume(self, name: str, volume_mul: float) -> None:
        """Seta o volume de um input (multiplicador 0..1).

        Args:
            name: Nome do input no OBS.
            volume_mul: Volume entre 0.0 (mute) e 1.0 (100%). Pode ir ate 20.0
                (overdriven), mas a UI limita em 1.0.
        """
        await self.call("SetInputVolume", {
            "inputName": name,
            "inputVolumeMul": float(volume_mul),
        })

    async def toggle_input_mute(self, name: str) -> bool:
        """Alterna mute de um input. Retorna o novo estado (mutado=True)."""
        data = await self.call("ToggleInputMute", {"inputName": name})
        return bool(data.get("inputMuted"))

    # ---------------------- Hotkeys ----------------------

    async def trigger_hotkey(
        self,
        key_id: str,
        shift: bool = False,
        control: bool = False,
        alt: bool = False,
        command: bool = False,
    ) -> None:
        """Dispara uma hotkey por nome de tecla (ex: ``OBS_KEY_F1``).

        Util pra acionar atalhos pre-configurados pelo usuario no OBS
        (Configuracoes -> Atalhos).

        Args:
            key_id: Identificador da tecla (ex: OBS_KEY_F1, OBS_KEY_F3).
            shift, control, alt, command: Modificadores.
        """
        await self.call(
            "TriggerHotkeyByKeySequence",
            {
                "keyId": key_id,
                "keyModifiers": {
                    "shift": shift,
                    "control": control,
                    "alt": alt,
                    "command": command,
                },
            },
        )

    async def open_scene_projector(
        self,
        scene_name: str,
        monitor_index: int = -1,
    ) -> None:
        """Abre uma cena como projector (janela separada).

        Args:
            scene_name: Nome da cena a projetar.
            monitor_index: Indice do monitor (0..n). Use ``-1`` para janela
                flutuante na tela atual.
        """
        params = {"sourceName": scene_name, "monitorIndex": monitor_index}
        await self.call("OpenSourceProjector", params)

    async def test_connection(
        self,
        host: str,
        port: int,
        password: str,
    ) -> dict[str, Any]:
        """Testa credenciais sem persistir nem afetar a conexao atual.

        Args:
            host, port, password: Credenciais a testar.

        Returns:
            Dicionario com ``ok``, ``message`` e (se sucesso) ``obs_version``.
        """
        if not _OBS_LIB_AVAILABLE:
            return {
                "ok": False,
                "message": "Lib simpleobsws nao instalada.",
                "obs_version": None,
            }
        url = f"ws://{host}:{port}"
        password_norm = (password or "").strip() or None
        params = simpleobsws.IdentificationParameters(
            ignoreNonFatalRequestChecks=False,
            eventSubscriptions=0,
        )
        client = simpleobsws.WebSocketClient(
            url=url,
            password=password_norm,
            identification_parameters=params,
        )
        try:
            await client.connect()
            ok = await client.wait_until_identified(timeout=15)
            if not ok:
                return {
                    "ok": False,
                    "message": (
                        "OBS aceitou conexao mas falhou identificar. "
                        "Verifique senha (sem espacos) e se autenticacao "
                        "esta habilitada do mesmo jeito nos dois lados."
                    ),
                    "obs_version": None,
                }
            response = await client.call(simpleobsws.Request("GetVersion"))
            if not response.ok():
                return {
                    "ok": False,
                    "message": f"GetVersion falhou: {response.requestStatus.comment}",
                    "obs_version": None,
                }
            return {
                "ok": True,
                "message": "Conexao OK.",
                "obs_version": response.responseData.get("obsVersion"),
            }
        except OSError as exc:
            return {
                "ok": False,
                "message": f"Conexao recusada em {url}: {exc}",
                "obs_version": None,
            }
        except Exception as exc:  # noqa: BLE001
            return {
                "ok": False,
                "message": f"{type(exc).__name__}: {exc}",
                "obs_version": None,
            }
        finally:
            with contextlib.suppress(Exception):
                await client.disconnect()
