@echo off
setlocal enabledelayedexpansion

REM start_prod.bat - versão com verificação pré-build e ajuste Dockerfile
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
echo Executando scripts\verify_deploy.py ...
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

REM 4) Garante que o Dockerfile contenha o trecho de atualizacao do pip (apenas se necessario)
if not exist "Dockerfile" (
  echo ERRO: Dockerfile nao encontrado na raiz.
  pause
  exit /b 1
)

echo.
echo Fazendo backup do Dockerfile...
set "BACKUP_DOCKERFILE=Dockerfile.bak.%DATE:~6,4%%DATE:~3,2%%DATE:~0,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%"
copy /Y Dockerfile "%BACKUP_DOCKERFILE%" >nul
if %ERRORLEVEL% neq 0 (
  echo Aviso: nao foi possivel criar backup do Dockerfile.
) else (
  echo Backup criado: %BACKUP_DOCKERFILE%
)

echo.
echo Verificando e inserindo trecho de atualizacao do pip no Dockerfile (se necessario)...
powershell -NoProfile -Command ^
  "$file='Dockerfile';" ^
  "if (-not (Select-String -Path $file -Pattern 'python -m pip install --upgrade pip setuptools wheel' -Quiet)) {" ^
  "  $text = Get-Content -Raw $file;" ^
  "  $pattern = 'COPY app/requirements.txt /app/requirements.txt';" ^
  "  if ($text -match [regex]::Escape($pattern)) {" ^
  "    $insert = $pattern + \"`nRUN python -m pip install --upgrade pip setuptools wheel`nRUN pip install --no-cache-dir -r /app/requirements.txt\";" ^
  "    $new = $text -replace [regex]::Escape($pattern), $insert;" ^
  "    Set-Content -Path $file -Value $new -Encoding UTF8;" ^
  "    Write-Host 'Trecho inserido no Dockerfile.';" ^
  "  } else { Write-Host 'Linha COPY app/requirements.txt /app/requirements.txt nao encontrada no Dockerfile. Nao foi inserido.'; exit 2 }" ^
  "} else { Write-Host 'Trecho ja presente no Dockerfile. Nada a fazer.' }"

if %ERRORLEVEL% neq 0 (
  echo.
  echo ERRO: falha ao tentar modificar o Dockerfile.
  echo Verifique manualmente: Dockerfile e a linha COPY app/requirements.txt /app/requirements.txt
  pause
  exit /b 1
)

REM 5) Se houve alteracao, comita automaticamente
for /f "delims=" %%F in ('git status --porcelain Dockerfile 2^>nul') do set GIT_CHANGES=%%F

if defined GIT_CHANGES (
  echo.
  echo Mudancas detectadas no Dockerfile. Commitando automaticamente...
  git add Dockerfile
  git commit -m "chore(docker): upgrade pip/setuptools/wheel in Dockerfile and install requirements during build" || (
    echo Aviso: git commit falhou. Verifique se o git esta configurado.
  )
) else (
  echo.
  echo Nenhuma mudanca no Dockerfile para commitar.
)

REM 6) Build e deploy (producao)
echo.
echo Construindo imagens de producao (backend e frontend) sem cache...
echo.

docker compose build backend --no-cache --progress=plain
if errorlevel 1 (
  echo.
  echo ERRO: falha ao construir a imagem do backend.
  pause
  exit /b 1
)

docker compose build frontend --no-cache --progress=plain
if errorlevel 1 (
  echo.
  echo ERRO: falha ao construir a imagem do frontend.
  pause
  exit /b 1
)

echo Subindo containers (docker compose up -d)...
docker compose up -d
if errorlevel 1 (
  echo.
  echo ERRO: falha ao subir containers.
  pause
  exit /b 1
)

echo Containers iniciados com sucesso.
timeout /t 3 /nobreak >nul

REM 7) Abre o navegador no frontend (porta 80)
REM Detecta IP local (fallback 127.0.0.1)
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
