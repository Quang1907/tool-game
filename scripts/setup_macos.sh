#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=== Setting up Binh 13 Analyzer on macOS ==="

# Check Python 3.11+
if command -v /opt/homebrew/bin/python3.11 >/dev/null 2>&1; then
    PYTHON_CMD="/opt/homebrew/bin/python3.11"
elif command -v python3.11 >/dev/null 2>&1; then
    PYTHON_CMD="python3.11"
else
    PYTHON_CMD="python3"
fi

echo "Using Python: $($PYTHON_CMD --version)"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment in .venv..."
    $PYTHON_CMD -m venv .venv
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Upgrading pip and installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup completed successfully!"
