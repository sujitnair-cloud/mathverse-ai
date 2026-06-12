@echo off
title MathVerse AI - Backend Server
echo =====================================
echo   MathVerse AI - Backend (FastAPI)
echo =====================================
echo.

cd /d "%~dp0backend"

REM Try anaconda python first, then system python
set PYTHON=C:\Users\Sujit\anaconda3\python.exe
if not exist "%PYTHON%" set PYTHON=python

echo Starting FastAPI server on http://localhost:8000
echo API docs at: http://localhost:8000/docs
echo Press Ctrl+C to stop
echo.

"%PYTHON%" -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
