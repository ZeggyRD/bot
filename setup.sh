#!/bin/bash
echo "Setting up OTWMusicSystem..."

# Check for Python 3.10+
if ! python3 -c 'import sys; assert sys.version_info >= (3,10)' &>/dev/null; then
    echo "Error: Python 3.10 or higher is required. Please install it and try again."
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment 'venv'..."
    python3 -m venv venv
else
    echo "Virtual environment 'venv' already exists."
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip and install requirements
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "Setup complete. Virtual environment 'venv' is ready and dependencies are installed."
    echo "To activate the environment, run: source venv/bin/activate"
else
    echo "Error: Failed to install dependencies."
    exit 1
fi

# Placeholder for smoke tests - to be added in a later phase
echo "Skipping smoke tests for now."
