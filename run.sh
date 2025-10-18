#!/bin/bash

# LATAM Vessel Tracking System - Startup Script

echo "========================================="
echo "LATAM Vessel Tracking System"
echo "========================================="
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found!"
    echo "Please run: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found!"
    echo "Please copy .env.example to .env and add your API key"
    exit 1
fi

# Check if API key is set
if grep -q "your_api_key_here" .env; then
    echo "Warning: Please set your AISSTREAM_API_KEY in the .env file"
    echo ""
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Run the application
echo "Starting vessel tracking system..."
echo ""
echo "Dashboard will be available at: http://localhost:5001"
echo "Press Ctrl+C to stop"
echo ""

python app.py
