@echo off
setlocal enabledelayedexpansion

REM ==========================================================
REM  MediaAutomationServer - build do instalador
REM  Verifica deps, gera .exe via PyInstaller, gera o
REM  instalador via Inno Setup. Tudo em um clique.
REM ==========================================================

cd /d "%~dp0\.."
set "ROOT=%CD%"

echo.
echo ==============================================
echo  MediaAutomationServer - Build do Instalador
echo ==============================================
echo.

REM ---------- 1. Mata processos do exe que possam estar rodando ----------
REM PyInstaller falha com "Acesso negado" se o exe anterior ainda esta
REM em execucao (launcher GUI, modo --server-mode, ou subprocess do uvicorn).
echo [1/7] Encerrando instancias anteriores em execucao...
taskkill /F /IM MediaAutomationServer.exe /T >nul 2>&1
taskkill /F /IM "MediaAutomationServer-Setup-*.exe" /T >nul 2>&1
REM Pequena pausa pra Windows liberar o lock no .exe.
timeout /t 1 /nobreak >nul

REM ---------- 2. Confere venv ----------
if not exist ".venv" (
    echo [setup] .venv nao encontrado. Criando...
    python -m venv .venv
    if errorlevel 1 (
        echo [erro] Falha ao criar venv. Verifique se Python esta no PATH.
        pause & exit /b 1
    )
)
call ".venv\Scripts\activate.bat"

REM ---------- 3. Sincroniza requirements ----------
echo [2/7] Sincronizando dependencias...
python -m pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet --upgrade-strategy only-if-needed
if errorlevel 1 (
    echo [erro] Falha ao instalar requirements.
    pause & exit /b 1
)

REM ---------- 4. Garante libs criticas ----------
call :ensure_lib segno
call :ensure_lib PySide6
call :ensure_lib PyInstaller pyinstaller

REM ---------- 5. Limpa builds antigos com retries ----------
echo [3/7] Limpando builds antigos...
call :force_rmdir build
call :force_rmdir dist
call :force_rmdir packaging\output

REM Confirma que dist\ realmente foi removida (ou pelo menos o exe).
if exist "dist\MediaAutomationServer.exe" (
    echo.
    echo [erro] Nao consegui remover o exe anterior em dist\.
    echo Provavel causa: o exe ainda esta em execucao em algum lugar.
    echo.
    echo Faca o seguinte:
    echo   1. Feche TODAS as janelas do MediaAutomationServer
    echo   2. Abra o Gerenciador de Tarefas e mate "MediaAutomationServer.exe"
    echo   3. Rode este script novamente
    pause & exit /b 1
)

REM ---------- 6. Build do .exe via PyInstaller ----------
echo [4/7] Compilando o .exe via PyInstaller...
pyinstaller "packaging\MediaAutomationServer.spec" --noconfirm --clean
if errorlevel 1 (
    echo.
    echo [erro] PyInstaller falhou. Veja o erro acima.
    echo Se for "Acesso negado" ao escrever o exe, alguma instancia
    echo do MediaAutomationServer ainda esta rodando. Mate ela no
    echo Gerenciador de Tarefas e rode novamente.
    pause & exit /b 1
)

if not exist "dist\MediaAutomationServer.exe" (
    echo [erro] PyInstaller nao gerou o .exe esperado em dist\.
    pause & exit /b 1
)
echo       OK: dist\MediaAutomationServer.exe gerado.

REM ---------- 7. Localiza Inno Setup 6 ----------
echo [5/7] Localizando Inno Setup 6...
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "C:\Program Files\Inno Setup 6\ISCC.exe" set "ISCC=C:\Program Files\Inno Setup 6\ISCC.exe"

if not defined ISCC (
    echo.
    echo ==============================================
    echo  [aviso] Inno Setup 6 nao encontrado.
    echo ==============================================
    echo  Baixe e instale: https://jrsoftware.org/isdl.php
    echo  Apos instalar, rode este script novamente.
    echo.
    echo  Alternativa: o .exe ja esta gerado em
    echo    %ROOT%\dist\MediaAutomationServer.exe
    echo  Voce pode distribuir esse exe diretamente.
    pause & exit /b 1
)
echo       OK: !ISCC!

REM ---------- 8. Compila o instalador ----------
echo [6/7] Compilando o instalador via Inno Setup...
"!ISCC!" "packaging\installer.iss"
if errorlevel 1 (
    echo [erro] Inno Setup falhou. Veja erros acima.
    pause & exit /b 1
)

REM ---------- 9. Verifica saida ----------
echo [7/7] Verificando saida...
set "OUTDIR=%ROOT%\packaging\output"
if not exist "!OUTDIR!" (
    echo [erro] Pasta packaging\output nao foi criada pelo Inno Setup.
    pause & exit /b 1
)

echo.
echo ==============================================
echo  Sucesso! Arquivos gerados:
echo ==============================================
echo.
echo  Executavel solto:
echo    %ROOT%\dist\MediaAutomationServer.exe
echo.
echo  Instalador (recomendado pra distribuir):
for %%F in ("!OUTDIR!\*.exe") do echo    %%F
echo.
echo ==============================================
pause
endlocal
exit /b 0


REM =============== Subroutines ===============

:ensure_lib
REM Garante uma lib instalada. Args: %1=nome import, %2=nome pip (opcional)
set "MODNAME=%~1"
set "PIPNAME=%~2"
if "%PIPNAME%"=="" set "PIPNAME=%~1"
python -c "import %MODNAME%" >nul 2>&1
if errorlevel 1 (
    echo       Instalando %PIPNAME%...
    pip install %PIPNAME% --quiet
    if errorlevel 1 (
        echo [erro] Falha ao instalar %PIPNAME%.
        pause & exit /b 1
    )
)
exit /b 0


:force_rmdir
REM Remove um diretorio com 3 tentativas (caso haja lock temporario).
set "TARGET=%~1"
if not exist "%TARGET%" exit /b 0
set "TRIES=0"
:_rmdir_loop
rmdir /s /q "%TARGET%" >nul 2>&1
if not exist "%TARGET%" exit /b 0
set /a TRIES+=1
if !TRIES! geq 3 (
    echo [warn] Nao consegui remover "%TARGET%" apos 3 tentativas.
    exit /b 0
)
timeout /t 1 /nobreak >nul
goto _rmdir_loop
