@echo off
cd /d "%~dp0"

echo Stopping and removing Docker Compose services (full)...
docker compose down --volumes --rmi all --remove-orphans
if %ERRORLEVEL% neq 0 (
  echo.
  echo ERRO: "docker compose down" retornou %ERRORLEVEL%.
  pause
  exit /b %ERRORLEVEL%
)

echo Running docker system prune -af
docker system prune -af

echo Running docker volume prune -f
docker volume prune -f

echo.
echo Full cleanup finished.
echo.
pause
