@echo off
title PayRoute AI - Launcher
color 0B
echo ========================================================
echo        PayRoute AI - Smart Payment Shield Platform
echo ========================================================
echo.

:: 1. Initialize SQLite database and seed defaults
echo [1/3] Initializing Database...
python database\init_db.py

echo.
:: 2. Launch FastAPI Backend
echo [2/3] Starting FastAPI Backend on http://127.0.0.1:8000...
start "PayRoute AI - Backend API" cmd /k "python -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"

:: 3. Brief wait for API startup
timeout /t 3 /nobreak >nul

:: 4. Launch Streamlit Customer Shield Dashboard
echo [3/3] Starting Streamlit Customer Shield on http://localhost:8501...
set PAYROUTE_API_URL=http://localhost:8000
start "PayRoute AI - Customer Dashboard" cmd /k "streamlit run dashboard\app.py"

echo.
echo ========================================================
echo PayRoute AI is now running!
echo - Customer Shield UI : http://localhost:8501
echo - Backend API Docs   : http://localhost:8000/docs
echo ========================================================
echo.
pause
