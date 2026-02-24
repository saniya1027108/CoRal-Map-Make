#!/usr/bin/env python3
"""
streamlit_app.py

Streamlit interface for Clinical Trial Data Extraction.
Provides all functionalities from the Flask app in a user-friendly Streamlit interface.

Run: streamlit run web/streamlit_app.py
"""
import sys
from pathlib import Path

# Add project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "experiment-scripts"))

import streamlit as st
import pandas as pd
from typing import Dict, Any, List, Optional

# Import services
from web.extraction_service import ExtractionService
from web.comparison_service import list_documents, load_comparison_data, get_dashboard_report
from web.highlight_service import get_highlights_for_column, resolve_pdf_path
from web.explainability_service import get_document_dashboard

# Page configuration
st.set_page_config(
    page_title="Clinical Trial Data Extraction",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for better styling with neon colors
st.markdown("""
<style>
    /* Hide sidebar completely */
    [data-testid="stSidebar"] {
        display: none;
    }
    
    /* Adjust main content margin */
    .main .block-container {
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: 100%;
    }
    
    .main-header {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
        background: linear-gradient(135deg, #1CD6CE 0%, #31E1F7 100%) !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        margin-bottom: 0.5rem !important;
        text-shadow: 0 0 30px rgba(28, 214, 206, 0.3) !important;
        filter: drop-shadow(0 0 15px rgba(49, 225, 247, 0.4)) !important;
    }
    .subtitle {
        font-size: 1.1rem !important;
        color: #666 !important;
        margin-bottom: 1rem !important;
        margin-top: 0 !important;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    .success-box {
        background-color: #1a3d2e;
        border-left: 4px solid #1CD6CE;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
        color: #1CD6CE;
        font-weight: 500;
    }
    
    .success-box strong {
        color: #31E1F7;
        font-weight: 700;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 4px solid #17a2b8;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    .result-card {
        background-color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .step-number {
        background-color: #1f77b4;
        color: white;
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-right: 0.5rem;
    }
    .comparison-table {
        width: 100%;
        border-collapse: collapse;
    }
    .comparison-table th, .comparison-table td {
        padding: 0.75rem;
        text-align: left;
        border-bottom: 1px solid #dee2e6;
    }
    .comparison-table th {
        background-color: #f8f9fa;
        font-weight: 600;
    }
    .highlight-match {
        background-color: #fff3cd;
        padding: 0.2rem 0.4rem;
        border-radius: 0.25rem;
    }
    
    /* Neon color styling for method selection buttons - AGGRESSIVE OVERRIDE */
    .method-selection-buttons {
        margin: 1rem 0;
    }
    
    /* Target ALL primary buttons in the method selection area with maximum specificity */
    .stButton button[kind="primary"],
    button[kind="primary"],
    .stButton > button,
    button[data-testid="baseButton-primary"],
    div[data-testid="column"] button,
    .method-selection-buttons button {
        background: linear-gradient(135deg, #1CD6CE 0%, #31E1F7 100%) !important;
        background-color: #1CD6CE !important;
        border: 2px solid #31E1F7 !important;
        color: #000000 !important;
        font-weight: 700 !important;
        font-size: 1.05rem !important;
        padding: 0.75rem 1.5rem !important;
        box-shadow: 0 4px 20px rgba(28, 214, 206, 0.5), 0 0 30px rgba(49, 225, 247, 0.3) !important;
        transition: all 0.3s ease !important;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.15) !important;
        border-radius: 0.5rem !important;
    }
    
    .stButton button[kind="primary"]:hover,
    button[kind="primary"]:hover,
    .stButton > button:hover,
    button[data-testid="baseButton-primary"]:hover,
    div[data-testid="column"] button:hover {
        background: linear-gradient(135deg, #31E1F7 0%, #1CD6CE 100%) !important;
        background-color: #31E1F7 !important;
        box-shadow: 0 6px 25px rgba(49, 225, 247, 0.7), 0 0 40px rgba(28, 214, 206, 0.5) !important;
        transform: translateY(-3px) scale(1.02) !important;
        border-color: #1CD6CE !important;
    }
    
    .stButton button[kind="primary"]:active,
    button[kind="primary"]:active,
    .stButton > button:active {
        transform: translateY(0px) scale(0.98) !important;
        box-shadow: 0 2px 15px rgba(28, 214, 206, 0.5), 0 0 20px rgba(49, 225, 247, 0.3) !important;
    }
    
    /* Ensure neon colors override Streamlit's default red/primary color */
    .stButton button[kind="primary"] p,
    button[kind="primary"] p,
    .stButton > button p {
        color: #000000 !important;
        font-weight: 700 !important;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'extraction_service' not in st.session_state:
        st.session_state.extraction_service = None
    if 'current_pdf_path' not in st.session_state:
        st.session_state.current_pdf_path = None
    if 'pdf_uploaded' not in st.session_state:
        st.session_state.pdf_uploaded = False
    if 'extraction_results' not in st.session_state:
        st.session_state.extraction_results = None
    if 'selected_method' not in st.session_state:
        st.session_state.selected_method = None
    if 'comparison_doc' not in st.session_state:
        st.session_state.comparison_doc = None


def get_extraction_service() -> Optional[ExtractionService]:
    """Get or create extraction service instance."""
    if st.session_state.extraction_service is None:
        try:
            st.session_state.extraction_service = ExtractionService()
        except Exception as e:
            st.error(f"⚠️ Could not initialize extraction service: {str(e)}")
            st.info("Please ensure GEMINI_API_KEY is set in your environment.")
            return None
    return st.session_state.extraction_service


def render_header():
    """Render the main header."""
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h1 class="main-header">🏥 Clinical Trial Data Extraction</h1>
        <p class="subtitle">AI-powered extraction of clinical trial data from PDF documents</p>
    </div>
    """, unsafe_allow_html=True)


def render_pdf_upload():
    """Render PDF upload section."""
    st.markdown("### 📄 Step 1: Upload PDF Document")
    
    uploaded_file = st.file_uploader(
        "Choose a PDF file",
        type=['pdf'],
        help="Maximum file size: 50MB"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        upload_dir = PROJECT_ROOT / 'web' / 'uploads'
        upload_dir.mkdir(exist_ok=True)
        
        pdf_path = upload_dir / uploaded_file.name
        
        with open(pdf_path, 'wb') as f:
            f.write(uploaded_file.getbuffer())
        
        # Load PDF into extraction service
        service = get_extraction_service()
        if service is not None:
            with st.spinner('Loading PDF...'):
                result = service.upload_pdf(str(pdf_path))
            
            if result.get('success'):
                st.session_state.pdf_uploaded = True
                st.session_state.current_pdf_path = str(pdf_path)
                
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #0a2f23 0%, #1a3d2e 100%); 
                            border-left: 5px solid #1CD6CE; 
                            padding: 1.2rem 1.5rem; 
                            border-radius: 0.75rem; 
                            margin: 1.5rem 0;
                            box-shadow: 0 4px 15px rgba(28, 214, 206, 0.2), 0 0 30px rgba(49, 225, 247, 0.1);">
                    <strong style="color: #1CD6CE; font-size: 1.1rem; font-weight: 700;">✓ PDF Loaded Successfully</strong><br>
                    <small style="color: #31E1F7; font-size: 0.95rem; margin-top: 0.5rem; display: inline-block;">
                        File: {uploaded_file.name} ({len(uploaded_file.getvalue()) / 1024 / 1024:.2f} MB)
                    </small>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error(f"❌ Failed to load PDF: {result.get('error')}")
                st.session_state.pdf_uploaded = False
    
    return st.session_state.pdf_uploaded


def render_method_selection():
    """Render extraction method selection."""
    st.markdown("### 🎯 Step 2: Select Extraction Method")
    
    # Add custom wrapper div for specific styling
    st.markdown('<div class="method-selection-buttons">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎯 Extract Value", use_container_width=True, type="primary", key="method_btn_extract"):
            st.session_state.selected_method = "single"
    
    with col2:
        if st.button("📋 Extract All Data", use_container_width=True, type="primary", key="method_btn_all"):
            st.session_state.selected_method = "all"
    
    with col3:
        if st.button("📊 Custom CSV", use_container_width=True, type="primary", key="method_btn_csv"):
            st.session_state.selected_method = "csv"
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Show method descriptions
    if st.session_state.selected_method == "single":
        st.info("📌 Extract value for a specific column from uploaded PDF")
    elif st.session_state.selected_method == "all":
        st.info("📌 View complete 133-column data from existing extractions")
    elif st.session_state.selected_method == "csv":
        st.info("📌 Extract custom columns from CSV file")


def render_single_extraction():
    """Render single column extraction form."""
    st.markdown("### 🎯 Extract Single Column Value")
    
    if st.button("← Back to Methods"):
        st.session_state.selected_method = None
        st.rerun()
    
    service = get_extraction_service()
    if service is None:
        return
    
    # Get available columns
    columns = service.get_available_columns()
    column_names = [col['column_name'] for col in columns]
    
    # Column selection
    st.markdown("#### Select Column")
    selected_column = st.selectbox(
        "Choose a column from the standard 133 columns",
        options=["-- Select a column --"] + column_names,
        key="single_column_select"
    )
    
    # Custom column option
    st.markdown("#### Or Enter Custom Column")
    custom_column = st.text_input(
        "Custom column name",
        placeholder="e.g., Trial Name",
        key="custom_column_name"
    )
    
    custom_definition = st.text_area(
        "Custom definition (optional)",
        placeholder="Enter column definition if using custom column name",
        key="custom_definition",
        height=100
    )
    
    # Extract button
    if st.button("Extract Value", type="primary", use_container_width=True):
        # Determine which column to extract
        column_to_extract = custom_column if custom_column else (selected_column if selected_column != "-- Select a column --" else None)
        definition = custom_definition if custom_column else None
        
        if not column_to_extract:
            st.error("Please select or enter a column name")
            return
        
        with st.spinner(f'Extracting value for "{column_to_extract}"...'):
            result = service.extract_single_column(column_to_extract, definition)
        
        if result.get('success'):
            st.session_state.extraction_results = {column_to_extract: result}
            st.success("✅ Extraction completed successfully!")
            render_extraction_results({column_to_extract: result})
        else:
            st.error(f"❌ Extraction failed: {result.get('error')}")


def render_all_extraction():
    """Render all columns extraction (view existing extractions)."""
    st.markdown("### 📋 Extract All Data")
    
    if st.button("← Back to Methods"):
        st.session_state.selected_method = None
        st.rerun()
    
    st.markdown("""
    <div class="info-box">
        <strong>📋 View Existing Extractions</strong><br>
        Select a document from the list below to view its complete 133-column extraction data.
        These are pre-extracted results from the baseline experiments.
    </div>
    """, unsafe_allow_html=True)
    
    # Get available documents
    with st.spinner("Loading available documents..."):
        documents = []
        results_dir = PROJECT_ROOT / 'experiment-scripts' / 'baselines_file_search_results' / 'gemini_native'
        
        if results_dir.exists():
            for model_dir in results_dir.iterdir():
                if model_dir.is_dir():
                    for doc_dir in model_dir.iterdir():
                        if doc_dir.is_dir():
                            extraction_file = doc_dir / 'extraction_metadata.json'
                            if extraction_file.exists():
                                documents.append({
                                    'id': f"{model_dir.name}/{doc_dir.name}",
                                    'name': doc_dir.name,
                                    'model': model_dir.name,
                                    'path': str(extraction_file)
                                })
        
        documents.sort(key=lambda x: x['name'])
    
    if not documents:
        st.warning("No existing extraction results found.")
        return
    
    # Document selection
    doc_options = {f"{doc['name']} ({doc['model']})": doc['id'] for doc in documents}
    selected_doc_display = st.selectbox(
        "Select Document",
        options=list(doc_options.keys()),
        key="all_doc_select"
    )
    
    if selected_doc_display and st.button("Load Extraction Data", type="primary", use_container_width=True):
        doc_id = doc_options[selected_doc_display]
        
        with st.spinner("Loading extraction data..."):
            import json
            extraction_file = results_dir / doc_id / 'extraction_metadata.json'
            
            if extraction_file.exists():
                with open(extraction_file, 'r', encoding='utf-8') as f:
                    extraction_data = json.load(f)
                
                # Transform to display format
                results = {}
                for col_name, col_data in extraction_data.items():
                    if not isinstance(col_data, dict):
                        continue
                    
                    results[col_name] = {
                        "column": col_name,
                        "value": col_data.get("value", "not found"),
                        "page_number": col_data.get("page", "Unknown"),
                        "modality": col_data.get("plan_source_type", "text"),
                        "evidence": col_data.get("evidence", ""),
                        "definition": col_data.get("definition", "")
                    }
                
                st.session_state.extraction_results = results
                st.success(f"✅ Loaded {len(results)} columns from {selected_doc_display}")
                render_extraction_results(results)


def render_csv_extraction():
    """Render CSV extraction form."""
    st.markdown("### 📊 Custom CSV Extraction")
    
    if st.button("← Back to Methods"):
        st.session_state.selected_method = None
        st.rerun()
    
    st.markdown("""
    <div class="info-box">
        <strong>CSV Format Requirements:</strong>
        <ul>
            <li>Must contain columns: <code>column_name</code> and <code>definition</code></li>
            <li>Example row: <code>NCT,"What national Clinical Trial identifier..."</code></li>
            <li>Use this option for custom columns not in the standard 133 set</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    uploaded_csv = st.file_uploader("Choose CSV file", type=['csv'], key="csv_upload")
    
    if uploaded_csv is not None:
        # Preview CSV
        import csv
        import io
        
        csv_content = uploaded_csv.getvalue().decode('utf-8')
        st.markdown("#### CSV Preview")
        df = pd.read_csv(io.StringIO(csv_content))
        st.dataframe(df.head(10), use_container_width=True)
        
        # Validate CSV
        csv_reader = csv.DictReader(io.StringIO(csv_content))
        headers = csv_reader.fieldnames
        
        headers_lower = [h.lower() for h in headers]
        has_column_name = 'column_name' in headers_lower or 'column name' in headers_lower
        has_definition = 'definition' in headers_lower
        
        if not (has_column_name and has_definition):
            st.error("❌ CSV must contain 'column_name' and 'definition' columns")
            return
        
        # Extract button
        if st.button("Extract from CSV", type="primary", use_container_width=True):
            service = get_extraction_service()
            if service is None:
                return
            
            csv_data = list(csv.DictReader(io.StringIO(csv_content)))
            
            with st.spinner(f'Extracting {len(csv_data)} columns from CSV...'):
                result = service.extract_from_csv(csv_data)
            
            if result.get('success'):
                st.session_state.extraction_results = result.get('results', {})
                st.success(f"✅ Extracted {result.get('total_columns')} columns successfully!")
                
                if result.get('errors'):
                    with st.expander("⚠️ Show errors"):
                        for error in result['errors']:
                            st.warning(error)
                
                render_extraction_results(result.get('results', {}))
            else:
                st.error(f"❌ Extraction failed: {result.get('error')}")


def render_extraction_results(results: Dict[str, Any]):
    """Render extraction results."""
    st.markdown("### 📊 Extraction Results")
    
    # Export buttons
    col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
    
    with col1:
        st.metric("Total Columns", len(results))
    
    with col2:
        # Export to JSON
        import json
        json_str = json.dumps(results, indent=2)
        st.download_button(
            "📥 Export JSON",
            data=json_str,
            file_name="extraction_results.json",
            mime="application/json"
        )
    
    with col3:
        # Export to CSV
        df_export = pd.DataFrame([
            {
                'Column Name': col_name,
                'Value': col_data.get('value', ''),
                'Page Number': col_data.get('page_number', ''),
                'Modality': col_data.get('modality', ''),
                'Evidence': col_data.get('evidence', ''),
                'Definition': col_data.get('definition', '')
            }
            for col_name, col_data in results.items()
        ])
        csv_str = df_export.to_csv(index=False)
        st.download_button(
            "📥 Export CSV",
            data=csv_str,
            file_name="extraction_results.csv",
            mime="text/csv"
        )
    
    with col4:
        view_mode = st.selectbox("View", ["Cards", "Table"], key="view_mode")
    
    st.markdown("---")
    
    # Display results
    if view_mode == "Cards":
        render_results_cards(results)
    else:
        render_results_table(results)


def render_results_cards(results: Dict[str, Any]):
    """Render results as cards."""
    for col_name, col_data in results.items():
        with st.container():
            st.markdown(f"""
            <div class="result-card">
                <h4 style="color: #1f77b4; margin-bottom: 0.5rem;">{col_name}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                value = col_data.get('value', col_data.get('primary_value', 'not found'))
                st.markdown(f"**Value:** {value}")
            
            with col2:
                page = col_data.get('page_number', col_data.get('page', 'Unknown'))
                st.markdown(f"**Page:** {page}")
            
            with col3:
                modality = col_data.get('modality', col_data.get('source_type', 'text'))
                st.markdown(f"**Modality:** {modality}")
            
            evidence = col_data.get('evidence', col_data.get('reasoning', ''))
            if evidence:
                with st.expander("🔍 View Evidence"):
                    st.text(evidence)
            
            st.markdown("---")


def render_results_table(results: Dict[str, Any]):
    """Render results as a table."""
    df = pd.DataFrame([
        {
            'Column Name': col_name,
            'Value': col_data.get('value', col_data.get('primary_value', 'not found')),
            'Page': col_data.get('page_number', col_data.get('page', 'Unknown')),
            'Modality': col_data.get('modality', col_data.get('source_type', 'text')),
            'Evidence': col_data.get('evidence', col_data.get('reasoning', ''))[:100] + '...' 
                       if len(col_data.get('evidence', col_data.get('reasoning', ''))) > 100 
                       else col_data.get('evidence', col_data.get('reasoning', ''))
        }
        for col_name, col_data in results.items()
    ])
    
    st.dataframe(df, use_container_width=True, height=600)


def render_top_navigation():
    """Render horizontal navigation bar at the top."""
    # Create navigation bar with styling
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a2332 0%, #293462 100%);
                padding: 0.5rem 1.5rem;
                border-radius: 0.75rem;
                margin-bottom: 2rem;
                border: 2px solid #1CD6CE;
                box-shadow: 0 4px 15px rgba(28, 214, 206, 0.2);">
        <p style="color: #1CD6CE; margin: 0; font-size: 0.9rem; font-weight: 600;">
            🧭 Navigation
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create horizontal navigation buttons
    col1, col2, col3 = st.columns([1, 1.2, 5])
    
    with col1:
        if st.button("🏠 Home", use_container_width=True, 
                    type="primary" if st.session_state.current_page == "Home" else "secondary",
                    key="nav_home",
                    help="Extract data from PDFs"):
            st.session_state.current_page = "Home"
            st.session_state.selected_method = None
            st.rerun()
    
    with col2:
        if st.button("📊 Compare Results", use_container_width=True,
                    type="primary" if st.session_state.current_page == "Compare" else "secondary",
                    key="nav_compare",
                    help="Compare extraction methods"):
            st.session_state.current_page = "Compare"
            st.rerun()
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)


def render_about_section():
    """Render about section on the home page."""
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(28, 214, 206, 0.1) 0%, rgba(49, 225, 247, 0.1) 100%);
                padding: 1.5rem 2rem;
                border-radius: 0.75rem;
                border-left: 4px solid #1CD6CE;
                margin-bottom: 2rem;
                box-shadow: 0 2px 10px rgba(28, 214, 206, 0.1);">
        <h3 style="color: #1CD6CE; margin-top: 0; font-weight: 700;">
            📋 About This Tool
        </h3>
        <p style="color: #31E1F7; margin-bottom: 1rem; line-height: 1.6;">
            Extract structured data from clinical trial PDFs using AI-powered analysis.
        </p>
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 1rem; margin-top: 1rem;">
            <div style="background-color: rgba(28, 214, 206, 0.05); padding: 1rem; border-radius: 0.5rem; border: 1px solid rgba(28, 214, 206, 0.2);">
                <strong style="color: #1CD6CE;">🎯 Single Column</strong>
                <p style="color: #31E1F7; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                    Extract specific data points
                </p>
            </div>
            <div style="background-color: rgba(28, 214, 206, 0.05); padding: 1rem; border-radius: 0.5rem; border: 1px solid rgba(28, 214, 206, 0.2);">
                <strong style="color: #1CD6CE;">📋 All Columns</strong>
                <p style="color: #31E1F7; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                    View 133 standard fields
                </p>
            </div>
            <div style="background-color: rgba(28, 214, 206, 0.05); padding: 1rem; border-radius: 0.5rem; border: 1px solid rgba(28, 214, 206, 0.2);">
                <strong style="color: #1CD6CE;">📊 Custom CSV</strong>
                <p style="color: #31E1F7; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                    Batch custom queries
                </p>
            </div>
            <div style="background-color: rgba(28, 214, 206, 0.05); padding: 1rem; border-radius: 0.5rem; border: 1px solid rgba(28, 214, 206, 0.2);">
                <strong style="color: #1CD6CE;">📄 PDF Evidence</strong>
                <p style="color: #31E1F7; font-size: 0.9rem; margin: 0.5rem 0 0 0;">
                    View highlighted sources
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main application."""
    initialize_session_state()
    
    # Initialize page state if not exists
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Home"
    
    # Top Navigation Bar
    render_top_navigation()
    
    # Main content based on selected page
    if st.session_state.current_page == "Home":
        render_header()
        
        # About section on home page
        render_about_section()
        
        # Step 1: Upload PDF
        pdf_uploaded = render_pdf_upload()
        
        if pdf_uploaded:
            st.markdown("---")
            
            # Step 2: Method selection
            if st.session_state.selected_method is None:
                render_method_selection()
            else:
                # Step 3: Show selected method form
                if st.session_state.selected_method == "single":
                    render_single_extraction()
                elif st.session_state.selected_method == "all":
                    render_all_extraction()
                elif st.session_state.selected_method == "csv":
                    render_csv_extraction()
    
    else:
        # Comparison page
        render_comparison_page()


def render_comparison_page():
    """Render comparison page."""
    from web.streamlit_comparison import render_comparison_interface
    render_comparison_interface()


if __name__ == "__main__":
    main()
