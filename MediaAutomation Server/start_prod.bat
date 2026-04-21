@echo off
setlocal enabledelayedexpansion

REM start_prod.bat - versão com verificação pré-build
echo ============================================================
echo Iniciando deploy de producao com verificacao pre-build
echo ============================================================

REM 1) Verifica se Python está disponível
python --version >nul 2>&1
if errorlevel 1 (
  echo ERRO: Python nao encontrado no PATH. Instale Python 3 e tente novamente.
  pause
  exit /b 1
)

REM 2) Executa o verificador
echo Executando scripts/verify_deploy.py ...
python scripts\verify_deploy.py
set "VERIFY_EXIT=%ERRORLEVEL%"

if "%VERIFY_EXIT%"=="0" (
  echo Verificacao concluida com sucesso.
) else (
  echo Verificacao retornou codigo %VERIFY_EXIT%. Abortando deploy.
  pause
  exit /b %VERIFY_EXIT%
)

REM 3) Verifica se Docker está disponível
docker info >nul 2>&1
if errorlevel 1 (
  echo ERRO: Docker nao parece estar rodando ou nao esta no PATH.
  pause
  exit /b 1
)

REM 4) Build e deploy (producao)
echo Construindo imagens de producao (docker compose build)...
docker compose build --no-cache
if errorlevel 1 (
  echo ERRO: falha ao construir imagens.
  pause
  exit /b 1
)

echo Subindo containers (docker compose up -d)...
docker compose up -d
if errorlevel 1 (
  echo ERRO: falha ao subir containers.
  pause
  exit /b 1
)

echo Containers iniciados com sucesso.
timeout /t 3 /nobreak >nul

REM 5) Abre o navegador no frontend (porta 80)
REM Detecta IP local
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
start "" "%FRONTEND_URL%"

echo Deploy concluido.
pause
endlocal
