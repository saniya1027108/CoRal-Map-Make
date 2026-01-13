#!/usr/bin/env python3
"""
Visualization script for extracted clinical trial data.
Generates an HTML report showing filled/null columns, grouped by category.
Serves the HTML via Python HTTP server and opens in browser.

Usage:
    python visualize_extraction.py <path_to_extracted_table.csv>
    python visualize_extraction.py test_results/new/NCT01715285_Fizazi_LATITUTE_NEJM'17/extracted_table.csv
"""

import sys
import json
import pandas as pd
from pathlib import Path
from collections import defaultdict
import webbrowser
import http.server
import socketserver
import threading
import time

def categorize_column(col_name):
    """Categorize column based on name patterns."""
    col_lower = col_name.lower()
    
    # Define category patterns
    if any(x in col_lower for x in ['age', 'sex', 'race', 'region', 'ps ']):
        return '👥 Demographics'
    elif any(x in col_lower for x in ['os', 'pfs', 'overall survival', 'progression']):
        return '📊 Survival Outcomes'
    elif any(x in col_lower for x in ['adverse', 'grade', 'toxicity']):
        return '⚠️ Adverse Events'
    elif any(x in col_lower for x in ['metasta', 'liver', 'lung', 'bone', 'nodal', 'volume']):
        return '🎯 Disease Characteristics'
    elif any(x in col_lower for x in ['treatment', 'regimen', 'arm', 'therapy', 'agent', 'docetaxel', 'control']):
        return '💊 Treatment Details'
    elif any(x in col_lower for x in ['orr', 'response rate', 'cr', 'sd', 'pd']):
        return '📈 Response Rates'
    elif any(x in col_lower for x in ['gleason', 'prostatectomy', 'radiotherapy', 'local therapy']):
        return '🏥 Clinical History'
    elif any(x in col_lower for x in ['author', 'year', 'nct', 'trial', 'phase', 'pubmed', 'endpoint']):
        return '📄 Study Metadata'
    elif any(x in col_lower for x in ['quality of life', 'qol']):
        return '😊 Quality of Life'
    else:
        return '📋 Other'

def load_metadata(csv_path):
    """Load metadata JSON if available."""
    metadata_path = Path(csv_path).parent / "extraction_metadata.json"
    if metadata_path.exists():
        with open(metadata_path, 'r') as f:
            return json.load(f)
    return None

def generate_html_report(csv_path, output_path=None):
    """Generate HTML visualization of extraction results."""
    csv_path = Path(csv_path)
    
    if not csv_path.exists():
        print(f"❌ Error: File not found: {csv_path}")
        return None
    
    # Read data
    df = pd.read_csv(csv_path)
    metadata = load_metadata(csv_path)
    
    # Get trial name
    trial_name = csv_path.parent.name
    
    # Analyze data
    total_cols = len(df.columns)
    filled_cols = df.notna().iloc[0].sum()
    null_cols = total_cols - filled_cols
    completion_pct = (filled_cols / total_cols * 100) if total_cols > 0 else 0
    
    # Group columns by category
    categories = defaultdict(list)
    for col in df.columns:
        value = df[col].iloc[0]
        is_filled = pd.notna(value) and str(value).strip() != ''
        
        # Get evidence from metadata if available
        evidence = None
        page = None
        if metadata and col in metadata:
            evidence = metadata[col].get('evidence')
            page = metadata[col].get('page')
        
        category = categorize_column(col)
        categories[category].append({
            'name': col,
            'value': value if is_filled else None,
            'filled': is_filled,
            'evidence': evidence,
            'page': page
        })
    
    # Sort categories
    category_order = [
        '📄 Study Metadata',
        '👥 Demographics',
        '💊 Treatment Details',
        '🎯 Disease Characteristics',
        '🏥 Clinical History',
        '📊 Survival Outcomes',
        '📈 Response Rates',
        '⚠️ Adverse Events',
        '😊 Quality of Life',
        '📋 Other'
    ]
    
    # Generate HTML
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Extraction Report: {trial_name}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        
        .header .trial-name {{
            font-size: 18px;
            opacity: 0.9;
            font-weight: 300;
        }}
        
        .summary {{
            display: flex;
            justify-content: space-around;
            padding: 30px;
            background: #f8f9fa;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .stat-card {{
            text-align: center;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            min-width: 150px;
        }}
        
        .stat-card .number {{
            font-size: 42px;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-card .label {{
            font-size: 14px;
            color: #6c757d;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        .stat-card.filled .number {{ color: #28a745; }}
        .stat-card.null .number {{ color: #dc3545; }}
        .stat-card.total .number {{ color: #667eea; }}
        
        .progress-bar {{
            width: 100%;
            height: 40px;
            background: #e9ecef;
            border-radius: 20px;
            overflow: hidden;
            margin: 20px 0;
            box-shadow: inset 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .progress-fill {{
            height: 100%;
            background: linear-gradient(90deg, #28a745 0%, #20c997 100%);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            transition: width 1s ease-out;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .category {{
            margin-bottom: 40px;
        }}
        
        .category-header {{
            font-size: 24px;
            font-weight: 600;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
            color: #2d3748;
        }}
        
        .category-stats {{
            font-size: 14px;
            color: #6c757d;
            margin-left: 10px;
        }}
        
        .columns-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 15px;
        }}
        
        .column-card {{
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #e9ecef;
            transition: all 0.2s;
        }}
        
        .column-card:hover {{
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            transform: translateY(-2px);
        }}
        
        .column-card.filled {{
            background: #d4edda;
            border-color: #28a745;
        }}
        
        .column-card.null {{
            background: #f8d7da;
            border-color: #dc3545;
        }}
        
        .column-name {{
            font-weight: 600;
            margin-bottom: 8px;
            color: #2d3748;
            word-break: break-word;
        }}
        
        .column-value {{
            padding: 8px;
            background: white;
            border-radius: 4px;
            margin-top: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            color: #495057;
            word-break: break-word;
        }}
        
        .null-indicator {{
            color: #dc3545;
            font-style: italic;
            font-size: 14px;
        }}
        
        .evidence {{
            margin-top: 8px;
            padding: 8px;
            background: #fff3cd;
            border-left: 3px solid #ffc107;
            border-radius: 4px;
            font-size: 12px;
            color: #856404;
        }}
        
        .page-badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            margin-left: 8px;
        }}
        
        .filter-bar {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 30px;
            display: flex;
            gap: 15px;
            align-items: center;
        }}
        
        .filter-button {{
            padding: 8px 16px;
            border: 2px solid #667eea;
            background: white;
            border-radius: 20px;
            cursor: pointer;
            transition: all 0.2s;
            font-size: 14px;
            color: #667eea;
        }}
        
        .filter-button:hover {{
            background: #667eea;
            color: white;
        }}
        
        .filter-button.active {{
            background: #667eea;
            color: white;
        }}
        
        footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #6c757d;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Clinical Trial Extraction Report</h1>
            <div class="trial-name">{trial_name}</div>
        </div>
        
        <div class="summary">
            <div class="stat-card filled">
                <div class="number">{filled_cols}</div>
                <div class="label">Filled</div>
            </div>
            <div class="stat-card null">
                <div class="number">{null_cols}</div>
                <div class="label">Null</div>
            </div>
            <div class="stat-card total">
                <div class="number">{total_cols}</div>
                <div class="label">Total</div>
            </div>
        </div>
        
        <div style="padding: 20px 40px;">
            <div class="progress-bar">
                <div class="progress-fill" style="width: {completion_pct:.1f}%">
                    {completion_pct:.1f}% Complete
                </div>
            </div>
        </div>
        
        <div class="content">
            <div class="filter-bar">
                <strong>Quick Filter:</strong>
                <button class="filter-button active" onclick="filterColumns('all')">All</button>
                <button class="filter-button" onclick="filterColumns('filled')">Filled Only</button>
                <button class="filter-button" onclick="filterColumns('null')">Null Only</button>
            </div>
"""
    
    # Add categories
    for category in category_order:
        if category not in categories:
            continue
        
        cols = categories[category]
        filled_in_cat = sum(1 for c in cols if c['filled'])
        total_in_cat = len(cols)
        
        html += f"""
            <div class="category">
                <div class="category-header">
                    {category}
                    <span class="category-stats">({filled_in_cat}/{total_in_cat} filled)</span>
                </div>
                <div class="columns-grid">
"""
        
        for col in cols:
            status = 'filled' if col['filled'] else 'null'
            value_html = ''
            
            if col['filled']:
                value_html = f'<div class="column-value">{col["value"]}</div>'
                if col['evidence']:
                    evidence_preview = col['evidence'][:150] + ('...' if len(col['evidence']) > 150 else '')
                    value_html += f'<div class="evidence">💬 "{evidence_preview}"</div>'
                if col['page']:
                    value_html += f'<span class="page-badge">Page {col["page"]}</span>'
            else:
                value_html = '<div class="null-indicator">⚠️ No value extracted</div>'
            
            html += f"""
                    <div class="column-card {status}" data-status="{status}">
                        <div class="column-name">{col['name']}</div>
                        {value_html}
                    </div>
"""
        
        html += """
                </div>
            </div>
"""
    
    # Close HTML
    html += """
        </div>
        
        <footer>
            Generated by CoRal-Map-Make Visualization Tool
        </footer>
    </div>
    
    <script>
        function filterColumns(filter) {
            // Update button states
            document.querySelectorAll('.filter-button').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            // Filter columns
            document.querySelectorAll('.column-card').forEach(card => {
                if (filter === 'all') {
                    card.style.display = 'block';
                } else {
                    card.style.display = card.dataset.status === filter ? 'block' : 'none';
                }
            });
        }
    </script>
</body>
</html>
"""
    
    # Save HTML
    if output_path is None:
        output_path = csv_path.parent / f"{trial_name}_visualization.html"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Visualization saved to: {output_path}")
    return output_path


def serve_html(html_path, port=8000):
    """Serve HTML file via HTTP server and open in browser."""
    html_path = Path(html_path).absolute()
    directory = html_path.parent
    filename = html_path.name
    
    # Find an available port
    original_port = port
    max_attempts = 10
    for attempt in range(max_attempts):
        try:
            # Test if port is available
            with socketserver.TCPServer(("", port), None) as test_server:
                break
        except OSError:
            port += 1
            if attempt == max_attempts - 1:
                print(f"❌ Could not find available port after {max_attempts} attempts")
                return
    
    if port != original_port:
        print(f"ℹ️  Port {original_port} busy, using port {port} instead")
    
    # Change to the directory containing the HTML
    import os
    original_dir = os.getcwd()
    os.chdir(directory)
    
    # Create server
    Handler = http.server.SimpleHTTPRequestHandler
    Handler.extensions_map['.html'] = 'text/html; charset=UTF-8'
    
    try:
        with socketserver.TCPServer(("", port), Handler) as httpd:
            url = f"http://localhost:{port}/{filename}"
            
            print("\n" + "="*60)
            print("🚀 HTTP Server Started!")
            print("="*60)
            print(f"📍 URL: {url}")
            print(f"📂 Serving from: {directory}")
            print("="*60)
            print("\n🌐 Opening in browser...")
            
            # Open browser after a short delay
            def open_browser():
                time.sleep(1)
                webbrowser.open(url)
            
            browser_thread = threading.Thread(target=open_browser)
            browser_thread.daemon = True
            browser_thread.start()
            
            print("\n✨ Visualization is now live!")
            print("💡 Press Ctrl+C to stop the server\n")
            
            # Serve until interrupted
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n🛑 Server stopped by user")
        print("✅ Goodbye!")
    except Exception as e:
        print(f"\n❌ Server error: {e}")
    finally:
        os.chdir(original_dir)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python visualize_extraction.py <path_to_extracted_table.csv>")
        print("\nExample:")
        print("  python visualize_extraction.py test_results/new/NCT01715285_Fizazi_LATITUTE_NEJM'17/extracted_table.csv")
        print("\nThis will:")
        print("  1. Generate HTML visualization")
        print("  2. Start a local HTTP server")
        print("  3. Open the visualization in your browser")
        print("  4. Keep serving until you press Ctrl+C")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    html_path = generate_html_report(csv_path)
    
    if html_path:
        print("\n" + "="*60)
        serve_html(html_path)
