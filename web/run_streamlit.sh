#!/bin/bash
# Launcher script for Streamlit interface

echo "================================================"
echo "Clinical Trial Data Extraction - Streamlit UI"
echo "================================================"
echo ""

# Check if GEMINI_API_KEY is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  Warning: GEMINI_API_KEY environment variable is not set"
    echo "   Please set it before running extractions:"
    echo "   export GEMINI_API_KEY='your-api-key-here'"
    echo ""
fi

# Check if streamlit is installed
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit is not installed"
    echo "   Installing dependencies..."
    pip install -r web/streamlit_requirements.txt
    echo ""
fi

echo "🚀 Starting Streamlit application..."
echo "   URL: http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo "================================================"
echo ""

# Run streamlit from project root
cd "$(dirname "$0")/.." || exit
streamlit run web/streamlit_app.py
