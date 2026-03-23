#!/bin/bash

echo ""
echo "========================================"
echo " Market Oracle - Build Script (Unix)"
echo "========================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.9+"
    exit 1
fi

# Check Node
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js not found. Please install Node.js 18+"
    exit 1
fi

echo "[1/4] Installing backend dependencies..."
cd backend
pip3 install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install Python dependencies"
    exit 1
fi

echo ""
echo "[2/4] Installing frontend dependencies..."
cd ../frontend
npm install
if [ $? -ne 0 ]; then
    echo "[ERROR] Failed to install npm dependencies"
    exit 1
fi

echo ""
echo "[3/4] Building frontend..."
npm run build
if [ $? -ne 0 ]; then
    echo "[ERROR] Frontend build failed"
    exit 1
fi

echo ""
echo "[4/4] Build complete!"
echo ""
echo "To start the server:"
echo "  cd backend"
echo "  python3 -m uvicorn app.main:app --reload"
echo ""
echo "Then open: http://localhost:8000"
echo ""
