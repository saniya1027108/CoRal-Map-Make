import os
import sys
import shutil

# Add project root to path for imports
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.chunking.chunking import process_pdf


if __name__ == "__main__":
    pdf_path = input("Enter the full path of your local research paper PDF: ").strip()
    
    if not pdf_path:
        print("❌ No path provided.")
        sys.exit(1)
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        sys.exit(1)
    
    # Extract PDF filename without extension (e.g., "NEJMoa1702900")
    pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
    
    # Create output directory structure: test_results/NEJMoa1702900/
    BASE_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../test_results")
    OUTPUT_DIR = os.path.join(BASE_OUTPUT_DIR, pdf_filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Define paths
    copied_pdf_path = os.path.join(OUTPUT_DIR, f"{pdf_filename}.pdf")
    json_output_path = os.path.join(OUTPUT_DIR, "pdf_chunked.json")
    
    # Copy the PDF to the output directory
    try:
        shutil.copy2(pdf_path, copied_pdf_path)
        print(f"✅ PDF copied to: {copied_pdf_path}")
    except Exception as e:
        print(f"⚠️  Warning: Could not copy PDF: {e}")
    
    # Process the PDF using the structured chunker
    process_pdf(pdf_path, output_path=json_output_path)
    
    print(f"\n✅ Results saved to: {OUTPUT_DIR}")
    print(f"   📄 PDF: {copied_pdf_path}")
    print(f"   📋 JSON: {json_output_path}")
    