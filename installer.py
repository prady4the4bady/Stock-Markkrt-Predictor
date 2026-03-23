#!/usr/bin/env python3
"""
Market Oracle - Cross-Platform Installer
Installs dependencies and launches the application on Windows/Mac/Linux
"""
import os
import sys
import subprocess
import platform
import shutil
from pathlib import Path

# Colors for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║   🔮 MARKET ORACLE - AI Stock & Crypto Predictions 🔮       ║
║                                                              ║
║   Ensemble ML: LSTM + Prophet + XGBoost                      ║
║   100% Free & Open Source                                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
{Colors.END}
""")

def check_python():
    """Check Python version"""
    print(f"{Colors.CYAN}[1/6]{Colors.END} Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print(f"{Colors.RED}❌ Python 3.9+ is required. Current: {version.major}.{version.minor}{Colors.END}")
        sys.exit(1)
    print(f"{Colors.GREEN}✓ Python {version.major}.{version.minor}.{version.micro}{Colors.END}")

def check_node():
    """Check Node.js installation"""
    print(f"{Colors.CYAN}[2/6]{Colors.END} Checking Node.js...")
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"{Colors.GREEN}✓ Node.js {version}{Colors.END}")
        return True
    except FileNotFoundError:
        print(f"{Colors.YELLOW}⚠ Node.js not found. Frontend features may be limited.{Colors.END}")
        return False

def install_backend():
    """Install Python backend dependencies"""
    print(f"\n{Colors.CYAN}[3/6]{Colors.END} Installing backend dependencies...")
    
    backend_dir = Path(__file__).parent / 'backend'
    requirements = backend_dir / 'requirements.txt'
    
    if not requirements.exists():
        print(f"{Colors.RED}❌ requirements.txt not found!{Colors.END}")
        return False
    
    # Create virtual environment (optional but recommended)
    venv_dir = backend_dir / 'venv'
    
    try:
        subprocess.run([
            sys.executable, '-m', 'pip', 'install', '-r', str(requirements)
        ], check=True)
        print(f"{Colors.GREEN}✓ Backend dependencies installed{Colors.END}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.RED}❌ Failed to install backend dependencies: {e}{Colors.END}")
        return False

def install_frontend():
    """Install frontend dependencies and build"""
    print(f"\n{Colors.CYAN}[4/6]{Colors.END} Installing frontend dependencies...")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    
    if not (frontend_dir / 'package.json').exists():
        print(f"{Colors.YELLOW}⚠ Frontend not found, skipping...{Colors.END}")
        return False
    
    try:
        # Install dependencies
        subprocess.run(['npm', 'install'], cwd=frontend_dir, check=True, shell=True)
        print(f"{Colors.GREEN}✓ Frontend dependencies installed{Colors.END}")
        
        # Build frontend
        print(f"\n{Colors.CYAN}[5/6]{Colors.END} Building frontend...")
        subprocess.run(['npm', 'run', 'build'], cwd=frontend_dir, check=True, shell=True)
        print(f"{Colors.GREEN}✓ Frontend built successfully{Colors.END}")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.YELLOW}⚠ Frontend build failed: {e}{Colors.END}")
        return False

def create_shortcuts():
    """Create platform-specific shortcuts"""
    print(f"\n{Colors.CYAN}[6/6]{Colors.END} Creating launch scripts...")
    
    base_dir = Path(__file__).parent
    system = platform.system()
    
    if system == 'Windows':
        # Create Windows batch file
        bat_content = f'''@echo off
cd /d "%~dp0"
echo Starting Market Oracle...
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
'''
        with open(base_dir / 'start-oracle.bat', 'w') as f:
            f.write(bat_content)
        print(f"{Colors.GREEN}✓ Created start-oracle.bat{Colors.END}")
        
    else:
        # Create Unix shell script
        sh_content = f'''#!/bin/bash
cd "$(dirname "$0")"
echo "Starting Market Oracle..."
cd backend
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
'''
        script_path = base_dir / 'start-oracle.sh'
        with open(script_path, 'w') as f:
            f.write(sh_content)
        os.chmod(script_path, 0o755)
        print(f"{Colors.GREEN}✓ Created start-oracle.sh{Colors.END}")

def launch_app():
    """Ask user if they want to launch the app"""
    print(f"\n{Colors.GREEN}{Colors.BOLD}✅ Installation complete!{Colors.END}")
    print(f"""
{Colors.CYAN}To start the application:{Colors.END}

  Windows:  Run {Colors.BOLD}start-oracle.bat{Colors.END} or:
            cd backend && python -m uvicorn app.main:app --reload
            
  Mac/Linux: Run {Colors.BOLD}./start-oracle.sh{Colors.END} or:
             cd backend && python3 -m uvicorn app.main:app --reload
             
  Docker:   {Colors.BOLD}docker-compose up -d{Colors.END}

{Colors.CYAN}Then open:{Colors.END} http://localhost:8000

{Colors.YELLOW}API Docs:{Colors.END} http://localhost:8000/docs
""")
    
    response = input(f"\n{Colors.CYAN}Would you like to start the server now? (y/n): {Colors.END}").strip().lower()
    
    if response == 'y':
        print(f"\n{Colors.GREEN}🚀 Starting Market Oracle...{Colors.END}")
        backend_dir = Path(__file__).parent / 'backend'
        os.chdir(backend_dir)
        
        try:
            subprocess.run([
                sys.executable, '-m', 'uvicorn', 
                'app.main:app', '--host', '127.0.0.1', '--port', '8000', '--reload'
            ])
        except KeyboardInterrupt:
            print(f"\n{Colors.YELLOW}Server stopped.{Colors.END}")

def main():
    print_banner()
    
    print(f"{Colors.BOLD}System: {platform.system()} {platform.release()}{Colors.END}\n")
    
    check_python()
    has_node = check_node()
    
    backend_ok = install_backend()
    
    if has_node:
        install_frontend()
    
    create_shortcuts()
    
    if backend_ok:
        launch_app()
    else:
        print(f"\n{Colors.RED}❌ Installation failed. Please check errors above.{Colors.END}")
        sys.exit(1)

if __name__ == '__main__':
    main()
