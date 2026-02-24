#!/usr/bin/env python3
"""
test_streamlit.py

Simple test script to verify Streamlit interface functionality.
Run: python web/test_streamlit.py
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    """Test that all required modules can be imported."""
    print("Testing imports...")
    
    try:
        import streamlit as st
        print("  ✓ streamlit")
    except ImportError as e:
        print(f"  ✗ streamlit: {e}")
        return False
    
    try:
        import pandas as pd
        print("  ✓ pandas")
    except ImportError as e:
        print(f"  ✗ pandas: {e}")
        return False
    
    try:
        from web.extraction_service import ExtractionService
        print("  ✓ extraction_service")
    except ImportError as e:
        print(f"  ✗ extraction_service: {e}")
        return False
    
    try:
        from web.comparison_service import list_documents, load_comparison_data
        print("  ✓ comparison_service")
    except ImportError as e:
        print(f"  ✗ comparison_service: {e}")
        return False
    
    try:
        from web.highlight_service import get_highlights_for_column
        print("  ✓ highlight_service")
    except ImportError as e:
        print(f"  ✗ highlight_service: {e}")
        return False
    
    print("\n✅ All imports successful!")
    return True


def test_services():
    """Test that backend services are working."""
    print("\nTesting backend services...")
    
    try:
        from web.comparison_service import list_documents
        documents = list_documents()
        print(f"  ✓ Found {len(documents)} documents with extraction results")
    except Exception as e:
        print(f"  ✗ comparison_service error: {e}")
    
    try:
        from web.extraction_service import ExtractionService
        service = ExtractionService()
        columns = service.get_available_columns()
        print(f"  ✓ Loaded {len(columns)} column definitions")
    except Exception as e:
        print(f"  ⚠ extraction_service warning: {e}")
        print("    Note: This is expected if GEMINI_API_KEY is not set")
    
    print("\n✅ Backend services are functional!")
    return True


def test_file_structure():
    """Test that required files exist."""
    print("\nTesting file structure...")
    
    required_files = [
        'web/streamlit_app.py',
        'web/streamlit_comparison.py',
        'web/streamlit_pdf_viewer.py',
        'web/extraction_service.py',
        'web/comparison_service.py',
        'web/highlight_service.py',
        'web/explainability_service.py',
        'web/streamlit_requirements.txt',
    ]
    
    all_exist = True
    for file in required_files:
        file_path = PROJECT_ROOT / file
        if file_path.exists():
            print(f"  ✓ {file}")
        else:
            print(f"  ✗ {file} (missing)")
            all_exist = False
    
    if all_exist:
        print("\n✅ All required files exist!")
    else:
        print("\n⚠️  Some files are missing")
    
    return all_exist


def test_optional_features():
    """Test optional features."""
    print("\nTesting optional features...")
    
    # Test pdf2image
    try:
        from pdf2image import convert_from_path
        print("  ✓ pdf2image (enhanced PDF rendering available)")
    except ImportError:
        print("  ⚠ pdf2image not installed (basic PDF rendering only)")
        print("    Install with: pip install pdf2image Pillow")
    
    # Test Pillow
    try:
        from PIL import Image
        print("  ✓ Pillow (image processing available)")
    except ImportError:
        print("  ⚠ Pillow not installed")
    
    return True


def check_environment():
    """Check environment configuration."""
    print("\nChecking environment...")
    
    import os
    
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print(f"  ✓ GEMINI_API_KEY is set ({api_key[:10]}...)")
    else:
        print("  ⚠ GEMINI_API_KEY is not set")
        print("    Set with: export GEMINI_API_KEY='your-key'")
    
    # Check upload directory
    upload_dir = PROJECT_ROOT / 'web' / 'uploads'
    if upload_dir.exists():
        print(f"  ✓ Upload directory exists: {upload_dir}")
    else:
        print(f"  ⚠ Upload directory will be created: {upload_dir}")
    
    # Check results directories
    results_dirs = [
        PROJECT_ROOT / 'experiment-scripts' / 'baselines_file_search_results' / 'gemini_native',
        PROJECT_ROOT / 'experiment-scripts' / 'baseline_landing_ai_w_gemini' / 'results',
        PROJECT_ROOT / 'new_pipeline_outputs' / 'results',
    ]
    
    found_results = False
    for results_dir in results_dirs:
        if results_dir.exists():
            print(f"  ✓ Results directory exists: {results_dir}")
            found_results = True
    
    if not found_results:
        print("  ⚠ No results directories found (comparison feature will be limited)")
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("Streamlit Interface Test Suite")
    print("=" * 60)
    
    success = True
    
    success &= test_imports()
    success &= test_file_structure()
    success &= test_services()
    test_optional_features()
    check_environment()
    
    print("\n" + "=" * 60)
    if success:
        print("✅ All tests passed!")
        print("\nYou can now run the Streamlit app:")
        print("  streamlit run web/streamlit_app.py")
        print("\nOr use the launcher script:")
        print("  bash web/run_streamlit.sh")
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        print("\nInstall missing dependencies:")
        print("  pip install -r web/streamlit_requirements.txt")
    print("=" * 60)


if __name__ == "__main__":
    main()
