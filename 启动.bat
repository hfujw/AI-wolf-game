@echo off
chcp 65001 >nul
title AI Wolf Game

set "ROOT_DIR=%~dp0"

echo.
echo   ========================================
echo       AI Wolf Game - Starting...
echo   ========================================
echo.

echo   [1/6] Checking Python...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Python not found.
    echo   [INFO] Run "INSTALL.bat" first to set up the environment.
    pause
    exit /b 1
)
echo   [OK] Python found.

echo.
echo   [2/6] Checking Node.js...
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo   [FAIL] Node.js not found.
    echo   [INFO] Run "INSTALL.bat" first to set up the environment.
    pause
    exit /b 1
)
echo   [OK] Node.js found.

echo.
echo   [3/6] Checking project dependencies...
python -c "import fastapi" 2>nul
if %errorlevel% neq 0 (
    echo   [FAIL] Python dependencies missing.
    echo   [INFO] Run "INSTALL.bat" first.
    pause
    exit /b 1
)

if not exist "%ROOT_DIR%frontend\node_modules" (
    echo   [FAIL] Frontend dependencies missing.
    echo   [INFO] Run "INSTALL.bat" first.
    pause
    exit /b 1
)
echo   [OK] All dependencies ready.

echo.
echo   [4/6] Checking config file...
if not exist "%ROOT_DIR%backend\.env" (
    (
        echo # AI Wolf Game - LLM Configuration
        echo LLM_API_KEY=86c4a679a2a146da8434da7675e27d62.ltS42pWtUWoNoQJq
        echo LLM_BASE_URL=https://open.bigmodel.cn/api/paas/v4/
        echo LLM_MODEL=GLM-4-Flash
    ) > "%ROOT_DIR%backend\.env"
    echo   [OK] Created backend\.env
) else (
    echo   [OK] backend\.env exists
)

echo.
echo   [5/6] Starting backend server (port 8000)...
start "AI-Wolf-Backend" /D "%ROOT_DIR%backend" cmd /c "python -m uvicorn main:app --host 0.0.0.0 --port 8000"

echo   Waiting for backend to be ready...
timeout /t 3 /nobreak >nul

echo.
echo   [6/6] Starting frontend server (port 3000)...
start "AI-Wolf-Frontend" /D "%ROOT_DIR%frontend" cmd /c "npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo   ========================================
echo     Start complete!
echo     Frontend : http://localhost:3000
echo     API Docs : http://localhost:8000/docs
echo   ========================================
echo.

start http://localhost:3000

pause
