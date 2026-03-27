@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  NexusTrader — Smart Startup Script  v3
::
::  Default : Dev mode  — uvicorn (direct) + Vite dev server
::  Flag    : --docker  — Docker Compose backend + Vite dev
::
::  Usage:
::    NexusTrader.bat            (dev mode)
::    NexusTrader.bat --docker   (Docker backend)
:: ============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "USE_DOCKER=0"
set "DOCKER_DESKTOP=C:\Program Files\Docker\Docker\Docker Desktop.exe"

:: Parse flags
for %%A in (%*) do if /i "%%A"=="--docker" set "USE_DOCKER=1"

title NexusTrader Launcher
mode con cols=70 lines=28
color 0A

echo.
echo  ============================================================
echo   NexusTrader  ^|  AI Stock ^& Crypto Predictor
echo  ============================================================
echo.

:: ── Dependency checks ──────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERROR] Python not found. Install Python 3.10+ from python.org
    pause & exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo  [ERROR] Node.js not found. Install Node.js 18+ from nodejs.org
    pause & exit /b 1
)

:: ── Install frontend dependencies if missing ───────────────────────────────
if not exist "%FRONTEND%\node_modules" (
    echo  [SETUP] Installing frontend dependencies...
    cd /d "%FRONTEND%"
    call npm install
    if errorlevel 1 (
        color 0C
        echo  [ERROR] npm install failed
        pause & exit /b 1
    )
    cd /d "%ROOT%"
)

:: ──────────────────────────────────────────────────────────────────────────
:: Docker detection (only when --docker flag is passed)
:: ──────────────────────────────────────────────────────────────────────────
if "%USE_DOCKER%"=="0" goto :launch_direct

echo  [Docker] Checking Docker engine...

docker version >nul 2>&1
if not errorlevel 1 goto :docker_ready

docker --context default version >nul 2>&1
if not errorlevel 1 (
    docker context use default >nul 2>&1
    goto :docker_ready
)

:: Neither context is up — try to start Docker Desktop
if not exist "%DOCKER_DESKTOP%" (
    color 0E
    echo  [WARN] Docker Desktop not found. Install from https://docker.com
    echo         Starting in direct dev mode instead.
    color 0A
    set "USE_DOCKER=0"
    goto :launch_direct
)

echo  [Docker] Starting Docker Desktop — please wait (up to 90 s)...
start "" "%DOCKER_DESKTOP%"

set /a DOCKER_WAIT=0
:wait_docker
timeout /t 3 /nobreak >nul
docker version >nul 2>&1
if not errorlevel 1 goto :docker_ready
docker --context default version >nul 2>&1
if not errorlevel 1 (
    docker context use default >nul 2>&1
    goto :docker_ready
)
set /a DOCKER_WAIT+=3
if !DOCKER_WAIT! lss 90 goto :wait_docker

color 0E
echo  [WARN] Docker engine did not become ready in 90 s.
echo         Open Docker Desktop manually then re-run with --docker.
echo         Starting in direct dev mode instead.
color 0A
set "USE_DOCKER=0"
goto :launch_direct

:docker_ready
echo  [Docker] Engine is ready.
goto :launch_docker


:: ──────────────────────────────────────────────────────────────────────────
:launch_direct
:: Direct dev mode: uvicorn (--reload) + Vite dev server
:: ──────────────────────────────────────────────────────────────────────────
echo  [Dev] Starting Backend  (http://localhost:8000)...
start "NexusTrader — Backend" cmd /k "%BACKEND%\start_backend.bat"

timeout /t 2 /nobreak >nul

echo  [Dev] Starting Frontend (http://localhost:5173)...
start "NexusTrader — Frontend" cmd /k "%FRONTEND%\start_frontend.bat"

goto :wait_and_open


:: ──────────────────────────────────────────────────────────────────────────
:launch_docker
:: Docker Compose mode: container backend + Vite dev server
:: ──────────────────────────────────────────────────────────────────────────
echo  [Docker] Building and starting containers...
cd /d "%ROOT%"
docker compose up --build -d
if errorlevel 1 (
    color 0C
    echo  [ERROR] docker compose failed.
    echo         Check logs: docker compose logs
    pause & exit /b 1
)
echo  [Docker] Container running on http://localhost:8000

timeout /t 2 /nobreak >nul

echo  [Dev] Starting Vite dev server (http://localhost:5173)...
start "NexusTrader — Frontend" cmd /k "%FRONTEND%\start_frontend.bat"

goto :wait_and_open


:: ──────────────────────────────────────────────────────────────────────────
:wait_and_open
:: Poll port 5173 until Vite is actually responding before opening the
:: browser.  This prevents the chrome-error://chromewebdata/ redirect
:: block that happens when the browser opens before Vite is ready.
:: ──────────────────────────────────────────────────────────────────────────
echo.
echo  Waiting for Vite to be ready...
set /a POLL=0

:poll_loop
powershell -NoProfile -Command "try{Invoke-WebRequest -Uri 'http://localhost:5173' -TimeoutSec 2 -UseBasicParsing | Out-Null; exit 0}catch{exit 1}" >nul 2>&1
if not errorlevel 1 goto :open_browser

set /a POLL+=1
if !POLL! geq 60 (
    echo  [WARN] Vite is taking longer than expected. Opening browser anyway...
    goto :open_browser
)
timeout /t 2 /nobreak >nul
goto :poll_loop


:open_browser
echo.
echo  ============================================================
echo.
echo   App      ^>  http://localhost:5173
echo   API      ^>  http://localhost:8000
echo   Docs     ^>  http://localhost:8000/docs
if "%USE_DOCKER%"=="1" echo   Docker   ^>  docker compose ps
echo.
echo  ============================================================
echo.
start "" "http://localhost:5173"
echo  Browser opened. You can close this window.
echo.
timeout /t 3 /nobreak >nul
exit
