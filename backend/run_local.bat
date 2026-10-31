@echo off
echo Starting Enugu Air Scanner Backend...
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
