#!/bin/bash

# WMATA API Startup Script

echo "======================================"
echo "WMATA API Server"
echo "======================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Run setup check
echo ""
echo "Running setup check..."
python check_setup.py

if [ $? -ne 0 ]; then
    echo ""
    echo "Setup check failed. Please fix the issues above."
    exit 1
fi

# Start server
echo ""
echo "======================================"
echo "Starting WMATA API Server..."
echo "======================================"
echo ""
echo "Server will be available at:"
echo "  http://localhost:5000"
echo "  ws://localhost:5000/ws"
echo ""
echo "Press Ctrl+C to stop"
echo ""

python app.py
