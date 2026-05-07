@echo off
setlocal

REM MediaAutomationServer - rodar o launcher (PySide6) em modo desenvolvimento.
cd /d "%~dp0"

if not exist ".venv" (
    echo [setup] Criando ambiente virtual...
    python -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo [setup] Sincronizando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet --upgrade-strategy only-if-needed
if errorlevel 1 (
    echo [erro] Falha ao instalar dependencias.
    pause
    exit /b 1
)

call :ensure_lib segno "QR code SVG"
call :ensure_lib PySide6 "interface grafica"

echo.
echo Abrindo o launcher...
echo.
python -m launcher.main

endlocal
exit /b 0

:ensure_lib
python -c "import %~1" >nul 2>&1
if errorlevel 1 (
    echo [setup] %~1 ^(%~2^) nao encontrado. Instalando...
    pip install %~1 --quiet
    if errorlevel 1 (
        echo [erro] Falha ao instalar %~1.
        pause
        exit /b 1
    )
)
exit /b 0
