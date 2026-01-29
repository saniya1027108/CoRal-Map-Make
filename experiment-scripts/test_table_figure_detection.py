#!/usr/bin/env python3
"""
Test script to validate table and figure detection logic.
Compares heuristic filtering vs current chunking results.

Usage:
    python experiment-scripts/test_table_figure_detection.py <pdf_path>
"""
import sys
import json
import fitz  # PyMuPDF
import pdfplumber
import re
from pathlib import Path
from collections import defaultdict

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class PageAnalyzer:
    """Analyze PDF pages for tables and figures using heuristics."""
    
    def __init__(self, pdf_path):
        self.pdf_path = pdf_path
        self.fitz_doc = fitz.open(pdf_path)
        self.plumber_doc = pdfplumber.open(pdf_path)
        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.fitz_doc.close()
        self.plumber_doc.close()
    
    def has_table_keyword(self, page_num):
        """Check if page text contains 'Table X' pattern."""
        page = self.fitz_doc[page_num]
        text = page.get_text()
        
        # Pattern: "Table 1", "Table 2", etc.
        pattern = r'\bTable\s+\d+[\s:.\-]'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        return bool(matches), matches
    
    def has_pdfplumber_table(self, page_num):
        """Check if pdfplumber detects table structure."""
        try:
            pl_page = self.plumber_doc.pages[page_num]
            tables = pl_page.extract_tables()
            
            if not tables:
                return False, 0
            
            # Filter out tiny "tables" (likely false positives)
            valid_tables = [t for t in tables if t and len(t) >= 2 and len(t[0]) >= 2]
            
            return len(valid_tables) > 0, len(valid_tables)
        except Exception as e:
            return False, 0
    
    def has_grid_pattern(self, page_num):
        """Check if page has grid-like text layout (potential table)."""
        page = self.fitz_doc[page_num]
        text = page.get_text()
        
        # Look for patterns indicating tabular data:
        # 1. Multiple lines with consistent spacing
        # 2. Repeated use of numbers/percentages
        # 3. Consistent column-like structure
        
        lines = text.split('\n')
        
        # Count lines with multiple numbers (potential data rows)
        number_pattern = r'\d+\.?\d*\s*%?'
        lines_with_numbers = sum(1 for line in lines if len(re.findall(number_pattern, line)) >= 3)
        
        # If many lines have multiple numbers, likely a table
        return lines_with_numbers >= 3, lines_with_numbers
    
    def has_figure_keyword(self, page_num):
        """Check if page text contains 'Figure X' pattern."""
        page = self.fitz_doc[page_num]
        text = page.get_text()
        
        # Pattern: "Figure 1", "Fig. 2", etc.
        pattern = r'\b(?:Figure|Fig\.?)\s+\d+[\s:.\-]'
        matches = re.findall(pattern, text, re.IGNORECASE)
        
        return bool(matches), matches
    
    def has_embedded_images(self, page_num):
        """Check if page has embedded images (potential figure)."""
        page = self.fitz_doc[page_num]
        images = page.get_images()
        
        # Filter out small images (logos, icons)
        large_images = [img for img in images if img[2] > 100 and img[3] > 100]  # width, height > 100px
        
        return len(large_images) > 0, len(large_images)
    
    def analyze_page(self, page_num):
        """Comprehensive analysis of a single page."""
        result = {
            'page': page_num + 1,
            'has_table': False,
            'has_figure': False,
            'details': {}
        }
        
        # Table detection
        table_keyword, table_matches = self.has_table_keyword(page_num)
        pdfplumber_table, num_tables = self.has_pdfplumber_table(page_num)
        grid_pattern, num_grid_lines = self.has_grid_pattern(page_num)
        
        result['details']['table_keyword'] = table_keyword
        result['details']['table_keyword_matches'] = table_matches
        result['details']['pdfplumber_tables'] = pdfplumber_table
        result['details']['num_pdfplumber_tables'] = num_tables
        result['details']['grid_pattern'] = grid_pattern
        result['details']['num_grid_lines'] = num_grid_lines
        
        # Overall table decision: any positive indicator
        result['has_table'] = table_keyword or pdfplumber_table or grid_pattern
        
        # Figure detection
        figure_keyword, figure_matches = self.has_figure_keyword(page_num)
        has_images, num_images = self.has_embedded_images(page_num)
        
        result['details']['figure_keyword'] = figure_keyword
        result['details']['figure_keyword_matches'] = figure_matches
        result['details']['has_images'] = has_images
        result['details']['num_images'] = num_images
        
        # Overall figure decision: keyword match + images
        result['has_figure'] = figure_keyword and has_images
        
        return result
    
    def analyze_all_pages(self):
        """Analyze all pages in the PDF."""
        results = []
        for page_num in range(len(self.fitz_doc)):
            results.append(self.analyze_page(page_num))
        return results


def load_current_chunks(pdf_path):
    """Load existing chunked JSON if available."""
    chunk_path = Path(pdf_path).parent / "pdf_chunked.json"
    if not chunk_path.exists():
        return None
    
    with open(chunk_path, 'r') as f:
        return json.load(f)


def compare_with_current_chunks(analysis_results, current_chunks):
    """Compare heuristic analysis with current chunking results."""
    print("\n" + "="*80)
    print("COMPARISON: Heuristic Filter vs Current Chunking")
    print("="*80)
    
    # Group current chunks by page
    chunks_by_page = defaultdict(list)
    for chunk in current_chunks:
        page = chunk.get('page')
        chunk_type = chunk.get('type')
        if isinstance(page, int):
            chunks_by_page[page].append(chunk_type)
    
    # Compare
    matches = {'table': 0, 'figure': 0}
    mismatches = {'table': [], 'figure': []}
    
    for result in analysis_results:
        page = result['page']
        current_types = chunks_by_page.get(page, [])
        
        # Table comparison
        heuristic_has_table = result['has_table']
        current_has_table = 'table' in current_types
        
        if heuristic_has_table == current_has_table:
            matches['table'] += 1
        else:
            mismatches['table'].append({
                'page': page,
                'heuristic': heuristic_has_table,
                'current': current_has_table,
                'details': result['details']
            })
        
        # Figure comparison
        heuristic_has_figure = result['has_figure']
        current_has_figure = 'figure' in current_types
        
        if heuristic_has_figure == current_has_figure:
            matches['figure'] += 1
        else:
            mismatches['figure'].append({
                'page': page,
                'heuristic': heuristic_has_figure,
                'current': current_has_figure,
                'details': result['details']
            })
    
    # Print results
    total_pages = len(analysis_results)
    
    print(f"\n📊 TABLES:")
    print(f"  Matches: {matches['table']}/{total_pages}")
    print(f"  Mismatches: {len(mismatches['table'])}")
    
    if mismatches['table']:
        print(f"\n  Mismatched Pages:")
        for m in mismatches['table'][:5]:  # Show first 5
            print(f"    Page {m['page']}: Heuristic={m['heuristic']}, Current={m['current']}")
            print(f"      Keyword: {m['details']['table_keyword']}, PDFPlumber: {m['details']['pdfplumber_tables']}, Grid: {m['details']['grid_pattern']}")
    
    print(f"\n📊 FIGURES:")
    print(f"  Matches: {matches['figure']}/{total_pages}")
    print(f"  Mismatches: {len(mismatches['figure'])}")
    
    if mismatches['figure']:
        print(f"\n  Mismatched Pages:")
        for m in mismatches['figure'][:5]:  # Show first 5
            print(f"    Page {m['page']}: Heuristic={m['heuristic']}, Current={m['current']}")
            print(f"      Keyword: {m['details']['figure_keyword']}, Images: {m['details']['has_images']}")


def print_analysis_summary(results):
    """Print summary of page analysis."""
    print("\n" + "="*80)
    print("PAGE ANALYSIS SUMMARY")
    print("="*80)
    
    table_pages = [r['page'] for r in results if r['has_table']]
    figure_pages = [r['page'] for r in results if r['has_figure']]
    both_pages = [r['page'] for r in results if r['has_table'] and r['has_figure']]
    neither_pages = [r['page'] for r in results if not r['has_table'] and not r['has_figure']]
    
    print(f"\nTotal pages: {len(results)}")
    print(f"\n📋 Pages with TABLES: {len(table_pages)}")
    print(f"   {table_pages}")
    
    print(f"\n📊 Pages with FIGURES: {len(figure_pages)}")
    print(f"   {figure_pages}")
    
    print(f"\n🔀 Pages with BOTH: {len(both_pages)}")
    print(f"   {both_pages}")
    
    print(f"\n📄 Pages with NEITHER (text only): {len(neither_pages)}")
    print(f"   {neither_pages}")
    
    # Detailed breakdown
    print("\n" + "-"*80)
    print("DETAILED PAGE-BY-PAGE BREAKDOWN")
    print("-"*80)
    
    for result in results:
        page = result['page']
        details = result['details']
        
        status = []
        if result['has_table']:
            reasons = []
            if details['table_keyword']:
                reasons.append(f"keyword: {details['table_keyword_matches']}")
            if details['pdfplumber_tables']:
                reasons.append(f"pdfplumber: {details['num_pdfplumber_tables']} tables")
            if details['grid_pattern']:
                reasons.append(f"grid: {details['num_grid_lines']} lines")
            status.append(f"TABLE ({', '.join(reasons)})")
        
        if result['has_figure']:
            reasons = []
            if details['figure_keyword']:
                reasons.append(f"keyword: {details['figure_keyword_matches']}")
            if details['has_images']:
                reasons.append(f"{details['num_images']} images")
            status.append(f"FIGURE ({', '.join(reasons)})")
        
        if not status:
            status.append("TEXT ONLY")
        
        print(f"Page {page:2d}: {' | '.join(status)}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_table_figure_detection.py <pdf_path>")
        sys.exit(1)
    
    pdf_path = sys.argv[1]
    
    if not Path(pdf_path).exists():
        print(f"Error: PDF not found: {pdf_path}")
        sys.exit(1)
    
    print("="*80)
    print(f"Testing Table/Figure Detection on: {Path(pdf_path).name}")
    print("="*80)
    
    # Analyze PDF
    with PageAnalyzer(pdf_path) as analyzer:
        results = analyzer.analyze_all_pages()
    
    # Print summary
    print_analysis_summary(results)
    
    # Load and compare with current chunks if available
    current_chunks = load_current_chunks(pdf_path)
    if current_chunks:
        compare_with_current_chunks(results, current_chunks)
    else:
        print("\n⚠️  No pdf_chunked.json found - skipping comparison")
    
    # Save results
    output_path = Path(pdf_path).parent / "page_analysis.json"
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\n💾 Detailed analysis saved to: {output_path}")
    
    print("\n" + "="*80)
    print("✅ Analysis complete!")
    print("="*80)


if __name__ == "__main__":
    main()
