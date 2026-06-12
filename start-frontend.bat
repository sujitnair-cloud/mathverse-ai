@echo off
title MathVerse AI - Frontend Dev Server
echo =====================================
echo   MathVerse AI - Frontend (React)
echo =====================================
echo.

REM Add Node.js to PATH if not already present
set PATH=C:\Program Files\nodejs;%PATH%

cd /d "%~dp0frontend"

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing npm packages...
    npm install
)

echo Starting Vite dev server on http://localhost:5173
echo Press Ctrl+C to stop
echo.

npm run dev

pause
