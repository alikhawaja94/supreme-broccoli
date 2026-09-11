@echo off
setlocal
cd /d "%~dp0"
title BeeSafe Telemetry 24/7 Launcher

:: Ensure ngrok and python are in PATH
set "PATH=%PATH%;%LOCALAPPDATA%\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe;%LOCALAPPDATA%\Microsoft\WinGet\Links;%LOCALAPPDATA%\Programs\Python\Python313"

:: Your permanent ngrok static domain
set NGROK_DOMAIN=defiant-ocelot-heap.ngrok-free.dev

echo ====================================================================
echo      BeeSafe AI Telemetry Server ^& ngrok 24/7 Service Launcher
echo ====================================================================
echo.
echo Permanent Domain: https://%NGROK_DOMAIN%
echo Local Server:     http://localhost:8000
echo.

echo [1/2] Launching Python Telemetry Server (Port 8000)...
start "BeeSafe Python Tracker" cmd /k "title Python Tracker Server (Port 8000) & python tracker_server.py"

timeout /t 2 /nobreak >nul

echo [2/2] Launching ngrok Tunnel (https://%NGROK_DOMAIN%)...
start "ngrok 24/7 Tunnel" cmd /k "title ngrok Tunnel (%NGROK_DOMAIN%) & ngrok http --domain=%NGROK_DOMAIN% 8000"

echo.
echo ====================================================================
echo [OK] Both services are running in their respective windows!
echo.
echo * Web Traffic Inspector: http://localhost:4040
echo * GitHub Pages Endpoint: https://%NGROK_DOMAIN%/api/telemetry
echo * Local Log File:        logs\visitor_logs.jsonl
echo * Plain Text Log:        logs\visitor_logs.txt
echo * Live Browser View:     http://localhost:8000/logs
echo ====================================================================
echo.
echo Keep both opened windows running for 24/7 logging.
echo.
pause
