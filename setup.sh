#!/bin/bash
set -e

echo "🚀 Setting up GPON God-Mode API..."

# Create Python virtual environment
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "📥 Installing Python requirements..."
pip install -r requirements.txt

# Install Playwright headless browsers
echo "🌐 Installing Playwright Chromium browser..."
playwright install chromium

echo "✅ Setup complete! You can now start the API with:"
echo "   source venv/bin/activate && python api.py"
