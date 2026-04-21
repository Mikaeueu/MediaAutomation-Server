@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM start_dev.bat
REM Inicia ambiente de desenvolvimento com Docker Compose,
REM abre o navegador no IP detectado e segue logs do frontend.
REM Coloque este arquivo na raiz do repositório (mesmo nível do docker-compose.yml)
REM ============================================================

echo ============================================================
echo Iniciando ambiente de desenvolvimento com Docker Compose
echo ============================================================

REM 1) Verifica se Docker está disponível
docker info >nul 2>&1
if errorlevel 1 (
  echo ERRO: Docker nao parece estar rodando ou nao esta no PATH.
  echo Abra o Docker Desktop e tente novamente.
  pause
  exit /b 1
)

REM 2) Verifica se docker compose esta disponivel
docker compose version >nul 2>&1
if errorlevel 1 (
  echo ERRO: 'docker compose' nao encontrado. Verifique sua instalacao do Docker.
  pause
  exit /b 1
)

REM 3) Detecta um IP local (IPv4) para uso em variaveis de ambiente
set "HOST_IP=127.0.0.1"
for /f "tokens=2 delims=:" %%A in ('ipconfig ^| findstr /i "IPv4"') do (
  for /f "tokens=* delims= " %%B in ("%%A") do (
    set "HOST_IP=%%B"
    goto :got_ip
  )
)
:got_ip
REM Remove possiveis espacos
for /f "tokens=* delims= " %%I in ("%HOST_IP%") do set "HOST_IP=%%I"

echo Detectado IP local: %HOST_IP%

REM 4) Gera arquivos .env para frontend e app/backend (sobrescreve se existirem)
echo Gerando frontend/.env.frontend e app/.env.app...

if not exist frontend (
  echo ERRO: pasta frontend nao encontrada. Certifique-se de que ./frontend existe.
  pause
  exit /b 1
)

if not exist app (
  echo ERRO: pasta app (backend) nao encontrada. Certifique-se de que ./app existe.
  pause
  exit /b 1
)

(
  echo VITE_API_BASE=http://%HOST_IP%:8000
  echo VITE_YT_REDIRECT=http://%HOST_IP%:8000/stream/youtube/callback
) > frontend/.env.frontend

(
  echo PYTHONUNBUFFERED=1
) > app/.env.app

REM Opcional: escreve .env na raiz para docker-compose se necessario
(
  echo VITE_API_BASE=http://%HOST_IP%:8000
  echo VITE_YT_REDIRECT=http://%HOST_IP%:8000/stream/youtube/callback
) > .env

echo .env files criados/atualizados.

REM 5) Build e up em modo desenvolvimento
echo Construindo e iniciando containers (docker compose up -d)...
docker compose up --build -d
if errorlevel 1 (
  echo ERRO: falha ao construir/subir containers.
  pause
  exit /b 1
)

echo Containers iniciados com sucesso.
echo Aguardando alguns segundos para inicializacao...
timeout /t 5 /nobreak >nul

REM 6) Abre o navegador no frontend (Vite dev server)
set "FRONTEND_URL=http://%HOST_IP%:5173"
echo Abrindo navegador em %FRONTEND_URL% ...
start "" "%FRONTEND_URL%"

REM 7) Segue logs do frontend (Ctrl+C para sair)
echo Seguindo logs do container frontend (pressione Ctrl+C para parar)...
docker compose logs -f frontend

echo ============================================================
echo Script finalizado.
echo ============================================================
pause
endlocal
