@echo off
title UPI Fraud Detection System
echo ========================================
echo   UPI Fraud Detection System Starting...
echo ========================================
echo.

cd /d "%~dp0"

echo Checking dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting Flask server...
echo Open your browser at: http://127.0.0.1:5000
echo Press CTRL+C to stop the server.
echo.

start "" http://127.0.0.1:5000
python app.py

pause
