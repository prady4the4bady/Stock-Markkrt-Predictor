@echo off
color 0B
title NexusTrader — Backend (FastAPI)

set "BACKEND=%~dp0"
set "VENV=%BACKEND%..\venv\Scripts\activate.bat"
if not exist "%VENV%" set "VENV=%BACKEND%..\.venv\Scripts\activate.bat"

cd /d "%BACKEND%"
if exist "%VENV%" call "%VENV%"

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo.
echo  ==================================================
echo   Backend  ^|  http://localhost:8000
echo   API Docs ^|  http://localhost:8000/docs
echo  ==================================================
echo.

python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
