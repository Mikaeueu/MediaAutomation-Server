@echo off
setlocal

REM MediaAutomationServer - launcher de desenvolvimento.
cd /d "%~dp0"

if not exist ".venv" (
    echo [setup] Criando ambiente virtual...
    python -m venv .venv
    if errorlevel 1 (
        echo [erro] Falha ao criar venv. Verifique se "python" esta no PATH.
        pause
        exit /b 1
    )
)

call ".venv\Scripts\activate.bat"

REM Sempre roda pip install em modo silencioso. E idempotente (rapido
REM se nada mudou) e garante que requirements.txt e o ambiente estejam
REM sempre em sincronia. Evita bugs de "lib X nao instalada".
echo [setup] Sincronizando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet --upgrade-strategy only-if-needed
if errorlevel 1 (
    echo.
    echo [erro] Falha ao instalar dependencias do requirements.txt.
    echo Rode manualmente para ver o erro completo:
    echo     pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM ---- Validacao explicita de libs criticas que ja deram problema ----
REM Algumas libs as vezes nao instalam mesmo apos pip install -r
REM (cache do pip, conflito transitivo, etc). Aqui validamos uma a uma
REM importando direto: se falhar, forcamos a instalacao isolada.

call :ensure_lib segno "QR code SVG"
REM Adicione novas linhas "call :ensure_lib <pacote> <descricao>" aqui
REM caso outra lib comece a apresentar problema.

goto :run_server

:ensure_lib
REM Subroutine: tenta importar a lib %1; se falhar, instala forcadamente.
python -c "import %~1" >nul 2>&1
if errorlevel 1 (
    echo [setup] %~1 ^(%~2^) nao encontrado. Instalando...
    pip install %~1 --quiet
    if errorlevel 1 (
        echo [erro] Falha ao instalar %~1. Rode manualmente:
        echo     pip install %~1
        pause
        exit /b 1
    )
    REM Confere de novo apos instalar.
    python -c "import %~1" >nul 2>&1
    if errorlevel 1 (
        echo [erro] %~1 instalou mas nao importa. Verifique seu ambiente.
        pause
        exit /b 1
    )
    echo [setup] %~1 instalado com sucesso.
) else (
    echo [setup] %~1 OK.
)
exit /b 0

:run_server

if not exist ".env" (
    echo [setup] Criando .env a partir do exemplo...
    copy ".env.example" ".env" >nul
)

echo.
echo ========================================
echo  MediaAutomationServer - iniciando
echo  Desktop: http://localhost:8000
echo  Mobile:  http://[IP_DO_PC]:8000/mobile
echo  Login:   midiadm / 123321
echo ========================================
echo.

REM Abre o navegador no PC apos 3s (em background).
start "" /b cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8000"

REM --reload monitora py/html/js/css pra dev fluido.
uvicorn app.main:app ^
    --host 0.0.0.0 ^
    --port 8000 ^
    --reload ^
    --reload-include "*.py" ^
    --reload-include "*.html" ^
    --reload-include "*.js" ^
    --reload-include "*.css"

endlocal
