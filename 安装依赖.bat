@echo off
chcp 65001 >nul
title AI Wolf Game

echo.
echo   ========================================
echo       AI Wolf Game - Install and Setup
echo   ========================================
echo.

echo   [1/6] Checking Python...
where python >nul 2>&1
if %errorlevel% equ 0 (
    python --version
) else (
    echo   Python not found. Trying winget install...
    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo   [FAIL] winget not available on this system.
        echo   [INFO] Please install Python 3.12+ manually:
        echo          https://www.python.org/downloads/
        echo   [INFO] Then run this script again.
        pause
        exit /b 1
    )
    winget install --id Python.Python.3.12 -e --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo   [FAIL] Python auto-install failed.
        echo   [INFO] Please install Python 3.12+ manually:
        echo          https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo   [OK] Python is now available.
)

echo.
echo   [2/6] Checking Node.js...
where node >nul 2>&1
if %errorlevel% equ 0 (
    node --version
) else (
    echo   Node.js not found. Trying winget install...
    where winget >nul 2>&1
    if %errorlevel% neq 0 (
        echo   [FAIL] winget not available on this system.
        echo   [INFO] Please install Node.js LTS manually:
        echo          https://nodejs.org/
        echo   [INFO] Then run this script again.
        pause
        exit /b 1
    )
    winget install --id OpenJS.NodeJS.LTS -e --accept-package-agreements --accept-source-agreements
    if %errorlevel% neq 0 (
        echo   [FAIL] Node.js auto-install failed.
        echo   [INFO] Please install Node.js LTS manually:
        echo          https://nodejs.org/
        pause
        exit /b 1
    )
    echo   [OK] Node.js is now available.
)

echo.
echo   [3/6] Installing Python dependencies...
cd /d "%~dp0backend"
python -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo   [FAIL] Python dependencies install failed.
    pause
    exit /b 1
)
echo   [OK] Python dependencies installed.

echo.
echo   [4/6] Installing frontend dependencies...
cd /d "%~dp0frontend"
call npm install
if %errorlevel% neq 0 (
    echo   [FAIL] Frontend dependencies install failed.
    pause
    exit /b 1
)
echo   [OK] Frontend dependencies installed.

echo.
echo   [5/6] Creating config file...
cd /d "%~dp0"
if not exist "backend\.env" (
    (
        echo # AI Wolf Game - LLM Configuration
        echo # Default uses Zhipu API (GLM-4-Flash). Change if needed.
        echo LLM_API_KEY=86c4a679a2a146da8434da7675e27d62.ltS42pWtUWoNoQJq
        echo LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
        echo LLM_MODEL=GLM-4-Flash
    ) > "backend\.env"
    echo   [OK] Created backend\.env with default config.
) else (
    echo   [OK] backend\.env already exists.
)

echo.
echo   [6/6] Creating data directory...
if not exist "backend\data" (
    mkdir "backend\data"
    echo   [OK] Created backend\data\ directory.
) else (
    echo   [OK] backend\data\ directory exists.
)

echo.
echo   ========================================
echo     All set! Run START.bat to play.
echo   ========================================
echo.
echo   Backend  : http://localhost:8000/docs
echo   Frontend : http://localhost:3000
echo.

pause
