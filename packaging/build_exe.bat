@echo off
setlocal

REM Constroi o exe via PyInstaller. Roda dentro do .venv.
cd /d "%~dp0\.."

if not exist ".venv" (
    echo [erro] .venv nao encontrado. Rode launcher.bat primeiro.
    pause
    exit /b 1
)

call ".venv\Scripts\activate.bat"

REM Garante PyInstaller instalado.
python -c "import PyInstaller" >nul 2>&1
if errorlevel 1 (
    echo [setup] Instalando PyInstaller...
    pip install pyinstaller --quiet
)

REM Limpa builds anteriores.
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"

echo.
echo Construindo o exe...
echo.
pyinstaller packaging\MediaAutomationServer.spec --noconfirm

if errorlevel 1 (
    echo [erro] Build falhou.
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Sucesso! Exe gerado em:
echo  dist\MediaAutomationServer.exe
echo.
echo  Para gerar o instalador:
echo  1. Instale o Inno Setup 6 ^(jrsoftware.org/isdl.php^)
echo  2. Abra packaging\installer.iss e clique em "Compile"
echo ========================================
pause

endlocal
