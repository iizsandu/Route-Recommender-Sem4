#!/bin/bash
echo "Crime Extraction Service"
echo "========================"
echo ""

if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Run: cp .env.example .env"
    exit 1
fi

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "Starting service on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""

uvicorn app.main:app --reload
