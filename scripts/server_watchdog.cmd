@echo off
rem Сторожевой скрипт сервера решения: поднимает Docker-контейнер и bore-туннель,
rem если они не запущены. Вызывается планировщиком каждые 5 минут.
cd /d "C:\Users\Administrator\Desktop\cosmohak\scripts"

rem --- контейнер с приложением ---
docker ps --format "{{.Names}}" 2>nul | find /I "cosmo" >nul
if errorlevel 1 (
  docker start cosmo >nul 2>&1
)

rem --- bore-туннель ---
tasklist /FI "IMAGENAME eq bore2.exe" 2>nul | find /I "bore2.exe" >nul
if errorlevel 1 (
  start "cosmo-bore" /min cmd /c "bore2.exe local 8501 --to bore.pub >> "%~dp0bore.log" 2>&1"
)
