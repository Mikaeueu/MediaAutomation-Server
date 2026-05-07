"""Endpoints da integracao OBS WebSocket.

Todos exigem autenticacao. Os endpoints sao async porque o ``simpleobsws``
e nativamente async.
"""

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.dependencies import get_current_user
from app.models.obs_config import ObsConfig
from app.repositories.hidden_scenes_repository import HiddenScenesRepository
from app.repositories.obs_config_repository import ObsConfigRepository
from app.schemas.obs_config import (
    ObsConfigRead,
    ObsConfigUpdate,
    ObsTestRequest,
    ObsTestResponse,
)
from app.services.obs_service import OBSConnectionError, OBSService


router = APIRouter(
    prefix="/api/obs",
    tags=["obs"],
    dependencies=[Depends(get_current_user)],
)


def get_repo() -> ObsConfigRepository:
    """FastAPI dependency: repositorio da config OBS."""
    return ObsConfigRepository()


def get_service() -> OBSService:
    """FastAPI dependency: servico OBS singleton."""
    return OBSService()


# ---------------------- Configuracao ----------------------


@router.get("/config", response_model=ObsConfigRead)
def read_config(repo: ObsConfigRepository = Depends(get_repo)) -> dict:
    """Retorna a configuracao atual do OBS WebSocket."""
    return repo.get().to_dict()


@router.put("/config", response_model=ObsConfigRead)
async def update_config(
    payload: ObsConfigUpdate,
    repo: ObsConfigRepository = Depends(get_repo),
    service: OBSService = Depends(get_service),
) -> dict:
    """Atualiza a configuracao do OBS WebSocket.

    Apos salvar, dropa a conexao atual pra forcar reconectar com os novos
    parametros na proxima request.
    """
    try:
        config = ObsConfig(
            host=payload.host,
            port=payload.port,
            password=payload.password,
            auto_connect=payload.auto_connect,
        )
        saved = repo.save(config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await service.disconnect()
    return saved.to_dict()


@router.post("/test", response_model=ObsTestResponse)
async def test_connection(
    payload: ObsTestRequest,
    service: OBSService = Depends(get_service),
) -> dict:
    """Testa as credenciais sem persistir nada."""
    return await service.test_connection(
        host=payload.host,
        port=payload.port,
        password=payload.password,
    )


# ---------------------- Status / conexao ----------------------


@router.get("/status")
async def status_endpoint(
    service: OBSService = Depends(get_service),
) -> dict:
    """Retorna status geral: conectado, versao, cena, gravacao."""
    return await service.get_status()


@router.post("/reconnect")
async def reconnect(service: OBSService = Depends(get_service)) -> dict:
    """Forca reconexao com o OBS."""
    try:
        await service.reconnect()
        return {"connected": True}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/disconnect")
async def disconnect(service: OBSService = Depends(get_service)) -> dict:
    """Desconecta do OBS (somente fechamento gracioso)."""
    await service.disconnect()
    return {"connected": False}


# ---------------------- Cenas ----------------------


@router.get("/scenes")
async def list_scenes(service: OBSService = Depends(get_service)) -> dict:
    """Lista todas as cenas e indica a atual."""
    try:
        return await service.list_scenes()
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/scenes/activate")
async def activate_scene(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Troca a cena atual.

    Body: ``{"name": "<nome_da_cena>"}``
    """
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' e obrigatorio.")
    try:
        await service.switch_scene(name)
        return {"current": name}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/scenes/hidden")
def list_hidden_scenes() -> dict:
    """Lista nomes de cenas ocultas pelo operador."""
    return {"hidden": HiddenScenesRepository().list_all()}


@router.post("/scenes/hide")
def hide_scene(payload: dict) -> dict:
    """Marca uma cena como oculta.

    Body: ``{"name": "<nome>"}``
    """
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' e obrigatorio.")
    HiddenScenesRepository().hide(name)
    return {"hidden": True, "name": name}


@router.post("/scenes/unhide")
def unhide_scene(payload: dict) -> dict:
    """Remove uma cena da lista de ocultas.

    Body: ``{"name": "<nome>"}``
    """
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' e obrigatorio.")
    HiddenScenesRepository().unhide(name)
    return {"hidden": False, "name": name}


@router.post("/scenes/projector")
async def open_projector(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Abre uma cena como projector (janela separada).

    Body: ``{"name": "<cena>", "monitor": -1}``
    ``monitor=-1`` abre como janela flutuante (default).
    """
    name = (payload or {}).get("name")
    monitor = (payload or {}).get("monitor", -1)
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' e obrigatorio.")
    try:
        await service.open_scene_projector(name, monitor_index=monitor)
        return {"opened": name, "monitor": monitor}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ---------------------- Scene collections ----------------------


@router.get("/scene-collections")
async def list_scene_collections(
    service: OBSService = Depends(get_service),
) -> dict:
    """Lista as scene collections cadastradas no OBS."""
    try:
        return await service.list_scene_collections()
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/scene-collections/activate")
async def activate_scene_collection(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Troca de scene collection. Body: ``{"name": "<collection>"}``."""
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' e obrigatorio.")
    try:
        await service.switch_scene_collection(name)
        return {"current": name}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ---------------------- Gravacao ----------------------


@router.post("/recording/start")
async def recording_start(
    service: OBSService = Depends(get_service),
) -> dict:
    """Inicia a gravacao. Idempotente (nao falha se ja gravando)."""
    try:
        await service.start_recording()
        return {"recording": True}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/recording/stop")
async def recording_stop(
    service: OBSService = Depends(get_service),
) -> dict:
    """Para a gravacao. Retorna o caminho do arquivo gravado, se houver."""
    try:
        result = await service.stop_recording()
        return {"recording": False, **result}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/recording/toggle")
async def recording_toggle(
    service: OBSService = Depends(get_service),
) -> dict:
    """Alterna entre iniciar e parar gravacao."""
    try:
        return await service.toggle_recording()
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


# ---------------------- Modos / outputs ----------------------


@router.post("/studio-mode/toggle")
async def studio_mode_toggle(
    service: OBSService = Depends(get_service),
) -> dict:
    """Alterna o Studio Mode (preview + program lado a lado)."""
    try:
        current = await service.get_studio_mode()
        new = await service.set_studio_mode(not current)
        return {"studio_mode": new}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/virtual-cam/toggle")
async def virtual_cam_toggle(
    service: OBSService = Depends(get_service),
) -> dict:
    """Alterna a Camera Virtual."""
    try:
        active = await service.toggle_virtual_cam()
        return {"virtual_cam": active}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/audio/inputs")
async def list_audio_inputs(
    service: OBSService = Depends(get_service),
) -> dict:
    """Lista inputs do OBS que tem audio (com volume e mute atual)."""
    try:
        return {"inputs": await service.list_audio_inputs()}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.put("/audio/volume")
async def set_input_volume(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Seta volume de um input. Body: ``{"name": "...", "volume_mul": 0.7}``."""
    name = (payload or {}).get("name")
    volume = (payload or {}).get("volume_mul")
    if not name or volume is None:
        raise HTTPException(status_code=400, detail="name e volume_mul obrigatorios.")
    try:
        await service.set_input_volume(name, float(volume))
        return {"ok": True}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/audio/mute/toggle")
async def toggle_input_mute(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Alterna mute de um input. Body: ``{"name": "..."}``."""
    name = (payload or {}).get("name")
    if not name:
        raise HTTPException(status_code=400, detail="Campo 'name' obrigatorio.")
    try:
        muted = await service.toggle_input_mute(name)
        return {"name": name, "muted": muted}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/hotkey/trigger")
async def trigger_hotkey(
    payload: dict,
    service: OBSService = Depends(get_service),
) -> dict:
    """Dispara uma hotkey do OBS. Body: ``{"key": "OBS_KEY_F1"}``.

    Modificadores opcionais: ``shift``, ``control``, ``alt``, ``command``.
    """
    key = (payload or {}).get("key")
    if not key:
        raise HTTPException(status_code=400, detail="Campo 'key' obrigatorio.")
    try:
        await service.trigger_hotkey(
            key_id=key,
            shift=bool((payload or {}).get("shift", False)),
            control=bool((payload or {}).get("control", False)),
            alt=bool((payload or {}).get("alt", False)),
            command=bool((payload or {}).get("command", False)),
        )
        return {"triggered": key}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/replay-buffer/toggle")
async def replay_buffer_toggle(
    service: OBSService = Depends(get_service),
) -> dict:
    """Alterna o Replay Buffer."""
    try:
        active = await service.toggle_replay_buffer()
        return {"replay_buffer": active}
    except OBSConnectionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
