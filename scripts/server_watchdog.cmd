@echo off
rem Сторож сервера решения (запускается планировщиком каждые 5 минут):
rem 1) поднимает Docker-контейнер с приложением, если остановлен;
rem 2) восстанавливает Tailscale Funnel (публичный HTTPS-адрес);
rem 3) поднимает резервный bore-туннель на постоянный порт 8261.
cd /d "%~dp0"

rem --- 1. Контейнер приложения ---
docker ps --format "{{.Names}}" 2>nul | find /I "cosmo" >nul
if errorlevel 1 (
  docker start cosmo >nul 2>&1
)

rem --- 2. Tailscale Funnel (публичный HTTPS-адрес) ---
set "TS=C:\Program Files\Tailscale\tailscale.exe"
if not exist "%TS%" goto :eof
"%TS%" funnel status 2>nul | find /I "8501" >nul
if errorlevel 1 (
  "%TS%" funnel --bg 8501 >nul 2>&1
)

rem --- 3. Bore-туннель (резервный адрес из замороженного README: bore.pub:8261) ---
tasklist /FI "IMAGENAME eq bore2.exe" 2>nul | find /I "bore2.exe" >nul
if errorlevel 1 (
  if exist "%~dp0bore2.exe" (
    start "cosmo-bore" /min cmd /c "bore2.exe local 8501 --to bore.pub --port 8261 >> "%~dp0bore.log" 2>&1"
  )
)
