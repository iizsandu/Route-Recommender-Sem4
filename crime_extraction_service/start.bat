@echo off
echo Crime Extraction Service
echo ========================
echo.

if not exist .env (
    echo ERROR: .env file not found!
    echo Run: copy .env.example .env
    exit /b 1
)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate.bat
pip install -q -r requirements.txt

echo.
echo Starting service on http://localhost:8000
echo API docs: http://localhost:8000/docs
echo.

uvicorn app.main:app --reload
