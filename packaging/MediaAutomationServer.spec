# PyInstaller spec - empacota o launcher como exe unico do Windows.
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_submodules

block_cipher = None
project_root = Path(SPECPATH).parent

extra_hidden = []
for pkg in ("pydantic", "pydantic_core", "pydantic_settings",
            "fastapi", "starlette", "uvicorn",
            "httpx", "httpcore", "websockets",
            "jose", "anyio", "sniffio"):
    try:
        extra_hidden += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [str(project_root / "launcher" / "main.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / "app" / "templates"), "app/templates"),
        (str(project_root / "app" / "static"), "app/static"),
        (str(project_root / ".env.example"), "."),
    ],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        "app", "app.main", "app.config", "app.database",
        "app.core.security", "app.core.dependencies",
        "app.routers.auth", "app.routers.holyrics",
        "app.routers.live_generator", "app.routers.network",
        "app.routers.obs", "app.routers.pages",
        "app.routers.service_types", "app.routers.shutdown",
        "app.services.auth_service", "app.services.holyrics_service",
        "app.services.network_service", "app.services.obs_service",
        "app.services.scheduler_service", "app.services.shutdown_service",
        "app.services.system_service",
        "app.services.title_generator_service",
        "simpleobsws",
        "segno",
        "bcrypt",
        "dotenv",
        "multipart", "python_multipart",
        "sqlite3",
        *extra_hidden,
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="MediaAutomationServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
