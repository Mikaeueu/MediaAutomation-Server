@echo off
rem start_prod.bat - suporta Dockerfile em app/ e frontend/
setlocal

rem garante execução a partir da pasta do script
pushd "%~dp0" 2>nul
if %ERRORLEVEL% NEQ 0 (
  echo ERRO: nao foi possivel mudar para o diretorio do script
  pause
  exit /b 1
)

rem limpa log anterior
if exist start_prod.log del /f /q start_prod.log

echo ============================================================ >> start_prod.log
echo Iniciando deploy de producao com verificacao pre-build >> start_prod.log
echo ============================================================ >> start_prod.log

rem -------------------------
rem Verifica Python
rem -------------------------
echo [STEP] Verificando Python...
echo [STEP] Verificando Python... >> start_prod.log
python --version >> start_prod.log 2>&1
if %ERRORLEVEL% NEQ 0 goto :err_python

rem -------------------------
rem Executa verificador
rem -------------------------
echo [STEP] Executando scripts\verify_deploy.py ...
echo [STEP] Executando scripts\verify_deploy.py ... >> start_prod.log
if not exist "scripts\verify_deploy.py" goto :err_no_verify
python "scripts\verify_deploy.py" >> start_prod.log 2>&1
set "VERIFY_EXIT=%ERRORLEVEL%"
echo [STEP] verify_deploy.py exit code: %VERIFY_EXIT% >> start_prod.log
if NOT "%VERIFY_EXIT%"=="0" goto :err_verify_failed

echo Verificacao concluida com sucesso.
echo Verificacao concluida com sucesso. >> start_prod.log

rem -------------------------
rem Verifica Docker
rem -------------------------
echo [STEP] Verificando Docker...
echo [STEP] Verificando Docker... >> start_prod.log
docker info >> start_prod.log 2>&1
if %ERRORLEVEL% NEQ 0 goto :err_docker

rem -------------------------
rem Localiza Dockerfiles
rem -------------------------
set "BACKEND_DOCKERFILE=%~dp0app\Dockerfile"
set "FRONTEND_DOCKERFILE=%~dp0frontend\Dockerfile"

set "FOUND_BACKEND=0"
set "FOUND_FRONTEND=0"

if exist "%BACKEND_DOCKERFILE%" set "FOUND_BACKEND=1"
if exist "%FRONTEND_DOCKERFILE%" set "FOUND_FRONTEND=1"

if "%FOUND_BACKEND%"=="0" (
  echo Aviso: Dockerfile do backend nao encontrado em app\Dockerfile. >> start_prod.log
) else (
  echo Dockerfile backend encontrado: %BACKEND_DOCKERFILE% >> start_prod.log
)

if "%FOUND_FRONTEND%"=="0" (
  echo Aviso: Dockerfile do frontend nao encontrado em frontend\Dockerfile. >> start_prod.log
) else (
  echo Dockerfile frontend encontrado: %FRONTEND_DOCKERFILE% >> start_prod.log
)

if "%FOUND_BACKEND%"=="0" if "%FOUND_FRONTEND%"=="0" goto :err_no_dockerfile_any

rem -------------------------
rem Backup e ensure para cada Dockerfile encontrado
rem -------------------------
if "%FOUND_BACKEND%"=="1" (
  echo [STEP] Backup e ensure backend Dockerfile... >> start_prod.log
  set "BACKUP_B=Dockerfile.app.bak.%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
  copy /Y "%BACKEND_DOCKERFILE%" "%BACKUP_B%" >> start_prod.log 2>&1
  echo Backup backend: %BACKUP_B% >> start_prod.log
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_dockerfile.ps1" -DockerfilePath "%BACKEND_DOCKERFILE%" >> start_prod.log 2>&1
  if %ERRORLEVEL% NEQ 0 goto :err_ps_failed
)

if "%FOUND_FRONTEND%"=="1" (
  echo [STEP] Backup e ensure frontend Dockerfile... >> start_prod.log
  set "BACKUP_F=Dockerfile.frontend.bak.%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
  copy /Y "%FRONTEND_DOCKERFILE%" "%BACKUP_F%" >> start_prod.log 2>&1
  echo Backup frontend: %BACKUP_F% >> start_prod.log
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\ensure_dockerfile.ps1" -DockerfilePath "%FRONTEND_DOCKERFILE%" >> start_prod.log 2>&1
  if %ERRORLEVEL% NEQ 0 goto :err_ps_failed
)

rem -------------------------
rem Commit automatico (opcional)
rem -------------------------
echo [STEP] (opcional) commit automatico se git presente... >> start_prod.log
where git >nul 2>&1
if %ERRORLEVEL% EQU 0 (
  rem commit apenas se houver mudanças nos Dockerfiles
  git add app/Dockerfile frontend/Dockerfile 2>nul
  for /f "delims=" %%F in ('git status --porcelain app/Dockerfile frontend/Dockerfile 2^>nul') do set GIT_CHANGES=%%F
  if defined GIT_CHANGES (
    git commit -m "chore(docker): ensure pip upgrade and install requirements in Dockerfiles" >> start_prod.log 2>&1
    if %ERRORLEVEL% NEQ 0 echo Aviso: git commit falhou. >> start_prod.log
  ) else (
    echo Nenhuma mudanca nos Dockerfiles para commitar. >> start_prod.log
  )
) else (
  echo Git nao encontrado; pulando commit automatico. >> start_prod.log
)

rem -------------------------
rem Build e deploy
rem -------------------------
echo [STEP] Construindo imagens (backend) >> start_prod.log
docker compose build backend --no-cache --progress=plain >> start_prod.log 2>&1
if %ERRORLEVEL% NEQ 0 goto :err_build_backend

echo [STEP] Construindo imagens (frontend) >> start_prod.log
docker compose build frontend --no-cache --progress=plain >> start_prod.log 2>&1
if %ERRORLEVEL% NEQ 0 goto :err_build_frontend

echo [STEP] Subindo containers >> start_prod.log
docker compose up -d >> start_prod.log 2>&1
if %ERRORLEVEL% NEQ 0 goto :err_up

echo Containers iniciados com sucesso.
echo Containers iniciados com sucesso. >> start_prod.log

timeout /t 3 /nobreak >nul

rem abre navegador
set "HOST_IP=127.0.0.1"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
  for /f "tokens=* delims= " %%B in ("%%A") do (
    set "HOST_IP=%%B"
    goto :got_ip
  )
)
:got_ip
for /f "tokens=* delims= " %%I in ("%HOST_IP%") do set "HOST_IP=%%I"

set "FRONTEND_URL=http://%HOST_IP%"
echo Abrindo navegador em %FRONTEND_URL% ...
echo Abrindo navegador em %FRONTEND_URL% ... >> start_prod.log
start "" "%FRONTEND_URL%"

echo Deploy concluido.
echo Deploy concluido. >> start_prod.log
pause

popd
endlocal
exit /b 0

rem -------------------------
rem Handlers de erro
rem -------------------------
:err_python
echo ERRO: Python nao encontrado no PATH. Instale Python 3 e tente novamente.
echo ERRO: Python nao encontrado no PATH. Instale Python 3 e tente novamente. >> start_prod.log
popd
pause
exit /b 1

:err_no_verify
echo ERRO: scripts\verify_deploy.py nao encontrado.
echo ERRO: scripts\verify_deploy.py nao encontrado. >> start_prod.log
popd
pause
exit /b 1

:err_verify_failed
echo Verificacao retornou codigo %VERIFY_EXIT%. Abortando deploy.
echo Verificacao retornou codigo %VERIFY_EXIT%. Abortando deploy. >> start_prod.log
popd
pause
exit /b %VERIFY_EXIT%

:err_docker
echo ERRO: Docker nao parece estar rodando ou nao esta no PATH.
echo ERRO: Docker nao parece estar rodando ou nao esta no PATH. >> start_prod.log
popd
pause
exit /b 1

:err_no_dockerfile_any
echo ERRO: Nenhum Dockerfile encontrado em app/ ou frontend/.
echo ERRO: Nenhum Dockerfile encontrado em app/ ou frontend/. >> start_prod.log
popd
pause
exit /b 1

:err_no_dockerfile
echo ERRO: Dockerfile nao encontrado na raiz do repositorio (%CD%).
echo ERRO: Dockerfile nao encontrado na raiz do repositorio (%CD%). >> start_prod.log
popd
pause
exit /b 1

:err_no_ps1
echo ERRO: scripts\ensure_dockerfile.ps1 nao encontrado.
echo ERRO: scripts\ensure_dockerfile.ps1 nao encontrado. >> start_prod.log
popd
pause
exit /b 1

:err_ps_failed
echo ERRO: falha ao executar scripts\ensure_dockerfile.ps1. Veja start_prod.log para detalhes.
echo ERRO: falha ao executar scripts\ensure_dockerfile.ps1. Veja start_prod.log para detalhes. >> start_prod.log
popd
pause
exit /b 1

:err_build_backend
echo ERRO: falha ao construir a imagem do backend.
echo ERRO: falha ao construir a imagem do backend. >> start_prod.log
popd
pause
exit /b 1

:err_build_frontend
echo ERRO: falha ao construir a imagem do frontend.
echo ERRO: falha ao construir a imagem do frontend. >> start_prod.log
popd
pause
exit /b 1

:err_up
echo ERRO: falha ao subir containers.
echo ERRO: falha ao subir containers. >> start_prod.log
popd
pause
exit /b 1
