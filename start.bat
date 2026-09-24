@echo off
REM =======================================================
REM DRPE - Optical Cryptography Web Suite
REM =======================================================

SET "NODE_PATH=D:\nodejs\node-v22.11.0-win-x64"
IF EXIST "%NODE_PATH%\node.exe" (
    SET "PATH=%NODE_PATH%;%PATH%"
    echo [Info] Using Node.js from %NODE_PATH%
)

echo.
echo [1/2] Launching DRPE FastAPI Backend (http://localhost:8000)...
start "DRPE Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn server:app --reload --host 0.0.0.0 --port 8000"

echo [2/2] Launching DRPE React Frontend (http://localhost:5173)...
start "DRPE Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo =======================================================
echo DRPE Suite is live:
echo   - Web UI:       http://localhost:5173
echo   - Backend API:  http://localhost:8000
echo   - Swagger Docs: http://localhost:8000/docs
echo =======================================================
echo.
pause
