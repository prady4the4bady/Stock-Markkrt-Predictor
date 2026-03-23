@echo off
setlocal enabledelayedexpansion

:: ============================================================
::  NexusTrader — Dev Startup Script
::  Starts backend (FastAPI) + frontend (Vite) in separate windows
:: ============================================================

set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"
set "BACKEND=%ROOT%\backend"
set "FRONTEND=%ROOT%\frontend"
set "VENV=%ROOT%\.venv\Scripts\activate.bat"

title NexusTrader Launcher

mode con cols=65 lines=22
color 0A

echo.
echo   =====================================================
echo    NexusTrader  ^|  AI Stock ^& Crypto Predictor
echo   =====================================================
echo.

:: ── Dependency checks ─────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [ERROR] Python not found. Install Python 3.10+
    pause & exit /b 1
)

node --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo   [ERROR] Node.js not found. Install Node.js 18+
    pause & exit /b 1
)

:: ── Check node_modules installed ──────────────────────────
if not exist "%FRONTEND%\node_modules" (
    echo   [SETUP] Installing frontend dependencies...
    echo.
    cd /d "%FRONTEND%"
    call npm install
    if errorlevel 1 (
        color 0C
        echo   [ERROR] npm install failed
        pause & exit /b 1
    )
    cd /d "%ROOT%"
)

:: ── Launch Backend ─────────────────────────────────────────
echo   Starting Backend  ^(http://localhost:8000^) ...
start "NexusTrader — Backend" cmd /k "^
    color 0B ^& ^
    title NexusTrader — Backend ^(FastAPI^) ^& ^
    cd /d ""%BACKEND%"" ^& ^
    if exist ""%VENV%"" call ""%VENV%"" ^& ^
    set PYTHONIOENCODING=utf-8 ^& ^
    set PYTHONUTF8=1 ^& ^
    echo. ^& ^
    echo   ================================================= ^& ^
    echo    Backend  ^|  http://localhost:8000 ^& ^
    echo    API Docs ^|  http://localhost:8000/docs ^& ^
    echo   ================================================= ^& ^
    echo. ^& ^
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

:: ── Wait 2s then launch Frontend ──────────────────────────
timeout /t 2 /nobreak >nul

echo   Starting Frontend ^(http://localhost:5173^) ...
start "NexusTrader — Frontend" cmd /k "^
    color 0A ^& ^
    title NexusTrader — Frontend ^(Vite^) ^& ^
    cd /d ""%FRONTEND%"" ^& ^
    echo. ^& ^
    echo   ================================================= ^& ^
    echo    Frontend  ^|  http://localhost:5173 ^& ^
    echo   ================================================= ^& ^
    echo. ^& ^
    npm run dev"

:: ── Wait for servers to boot then open browser ────────────
timeout /t 4 /nobreak >nul

echo.
echo   =====================================================
echo    Both servers are starting up...
echo.
echo    App     ^>  http://localhost:5173
echo    API     ^>  http://localhost:8000
echo    Docs    ^>  http://localhost:8000/docs
echo   =====================================================
echo.

:: Open browser
start "" "http://localhost:5173"

echo   Browser opened. You can close this window.
echo.
timeout /t 5 /nobreak >nul
exit
