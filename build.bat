@echo off
echo.
echo  ========================================
echo   Market Oracle - Build Script (Windows)
echo  ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.9+
    pause
    exit /b 1
)

REM Check Node
node --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Node.js not found. Please install Node.js 18+
    pause
    exit /b 1
)

echo [1/4] Installing backend dependencies...
cd backend
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install Python dependencies
    pause
    exit /b 1
)

echo.
echo [2/4] Installing frontend dependencies...
cd ..\frontend
call npm install
if errorlevel 1 (
    echo [ERROR] Failed to install npm dependencies
    pause
    exit /b 1
)

echo.
echo [3/4] Building frontend...
call npm run build
if errorlevel 1 (
    echo [ERROR] Frontend build failed
    pause
    exit /b 1
)

echo.
echo [4/4] Build complete!
echo.
echo To start the server:
echo   cd backend
echo   python -m uvicorn app.main:app --reload
echo.
echo Then open: http://localhost:8000
echo.
pause
