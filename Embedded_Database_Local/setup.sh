#!/bin/bash
# Setup script for Document Processing System

echo "======================================================================"
echo "Document Processing System - Setup"
echo "======================================================================"
echo

# Check Python version
echo "Checking Python version..."
python_version=$(python3 --version 2>&1 | awk '{print $2}')
echo "Found Python $python_version"

required_version="3.10"
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "ERROR: Python 3.10 or higher required"
    exit 1
fi

# Create virtual environment
echo
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create directories
echo
echo "Creating data directories..."
mkdir -p data/{input,processed,failed,chromadb,logs}

# Create .env file if it doesn't exist
if [ ! -f .env ]; then
    echo
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "IMPORTANT: Edit .env and add your GEMINI_API_KEY"
else
    echo
    echo ".env file already exists"
fi

# Check for Tesseract
echo
echo "Checking for Tesseract OCR..."
if command -v tesseract &> /dev/null; then
    tesseract_version=$(tesseract --version 2>&1 | head -n1)
    echo "Found: $tesseract_version"
else
    echo "WARNING: Tesseract not found"
    echo "Install with:"
    echo "  macOS:   brew install tesseract"
    echo "  Ubuntu:  sudo apt-get install tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng"
fi

echo
echo "======================================================================"
echo "Setup Complete!"
echo "======================================================================"
echo
echo "Next steps:"
echo "1. Edit .env and add your GEMINI_API_KEY"
echo "2. Place documents in data/input/"
echo "3. Run: python main.py"
echo
echo "To activate the virtual environment in the future:"
echo "  source venv/bin/activate"
echo
echo "To search the database:"
echo "  python query_interface.py"
echo
