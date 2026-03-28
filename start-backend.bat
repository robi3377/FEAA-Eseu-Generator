@echo off
cd /d "%~dp0backend"
pip install -r requirements.txt
echo.
echo Starting server at http://localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
pause
