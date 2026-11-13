@echo off
start "ViralCut Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000"
start "ViralCut Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"
echo ViralCut AI starting...
echo Backend: http://127.0.0.1:8000
echo Frontend: http://localhost:5173