"""
streamlit_comparison.py

Streamlit interface for comparing extraction results across multiple methods
with PDF highlighting and attribution visualization.
"""
import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional
import base64

from web.comparison_service import (
    list_documents, 
    load_comparison_data, 
    get_dashboard_report
)
from web.highlight_service import (
    get_highlights_for_column,
    resolve_pdf_path
)
from web.explainability_service import get_document_dashboard


def render_comparison_interface():
    """Render the main comparison interface."""
    # Add custom CSS for comparison page
    st.markdown("""
    <style>
        .doc-card {
            background-color: #293462;
            padding: 1.5rem;
            border-radius: 0.75rem;
            border: 2px solid #1CD6CE;
            margin-bottom: 1rem;
            box-shadow: 0 4px 15px rgba(28, 214, 206, 0.2), 0 0 20px rgba(41, 52, 98, 0.3);
            transition: all 0.3s ease;
            cursor: pointer;
        }
        
        .doc-card:hover {
            border-color: #31E1F7;
            box-shadow: 0 6px 25px rgba(49, 225, 247, 0.4), 0 0 35px rgba(28, 214, 206, 0.3);
            transform: translateY(-3px) scale(1.02);
        }
        
        .doc-card h4 {
            color: #1CD6CE;
            margin-bottom: 0.75rem;
            font-weight: 700;
        }
        
        .doc-card p {
            color: #31E1F7;
            font-size: 0.9rem;
            margin: 0;
        }
        
        /* Expander styling for column groups */
        .streamlit-expanderHeader {
            background-color: #1a2332 !important;
            border-left: 3px solid #1CD6CE !important;
            border-radius: 0.5rem !important;
        }
        
        /* Button styling for column selection */
        button[kind="secondary"] {
            background-color: #1a2332 !important;
            border: 1px solid #1CD6CE !important;
            color: #1CD6CE !important;
        }
        
        button[kind="secondary"]:hover {
            background-color: #293462 !important;
            border-color: #31E1F7 !important;
            transform: translateY(-2px) !important;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Page header
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 style="background: linear-gradient(135deg, #1CD6CE 0%, #31E1F7 100%);
                   -webkit-background-clip: text;
                   -webkit-text-fill-color: transparent;
                   background-clip: text;
                   font-size: 2.5rem;
                   font-weight: 700;
                   margin-bottom: 0.5rem;">
            📊 Compare Extraction Results
        </h1>
        <p style="color: #666; font-size: 1.1rem;">
            Compare results across Gemini, Landing AI, and pipeline methods
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Initialize session state
    if 'selected_comparison_doc' not in st.session_state:
        st.session_state.selected_comparison_doc = None
    if 'selected_column' not in st.session_state:
        st.session_state.selected_column = None
    if 'selected_group' not in st.session_state:
        st.session_state.selected_group = None
    
    # Check if we should show document list or detail
    if st.session_state.selected_comparison_doc is None:
        render_document_list()
    else:
        render_document_detail()


def render_document_list():
    """Render list of available documents."""
    with st.spinner("Loading documents..."):
        documents = list_documents()
    
    if not documents:
        st.warning("📭 No extraction results found. Run extractions via the pipeline or baselines to see documents here.")
        return
    
    st.success(f"Found {len(documents)} documents with extraction results")
    
    # Search/filter
    search = st.text_input("🔍 Search documents", placeholder="Enter document name...")
    
    # Filter documents
    if search:
        documents = [doc for doc in documents if search.lower() in doc['pdf_stem'].lower()]
    
    # Display documents as cards
    st.markdown("### Available Documents")
    
    # Create grid layout
    cols = st.columns(3)
    
    for idx, doc in enumerate(documents):
        col = cols[idx % 3]
        
        with col:
            with st.container():
                # Show available methods
                methods = doc.get('methods_available', [])
                method_labels = {
                    'gemini_native': '🟣 Gemini',
                    'landing_ai_baseline': '🟡 Landing AI',
                    'pipeline': '🔵 Pipeline',
                    'pipeline_plan_extract': '🔵 Pipeline (plan)',
                    'pipeline_keywords': '🔵 Pipeline + KW'
                }
                
                method_str = ", ".join([method_labels.get(m, m) for m in methods[:3]])
                
                st.markdown(f"""
                <div class="doc-card">
                    <h4>{doc['pdf_stem']}</h4>
                    <p>Methods: {method_str}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"View Details →", key=f"view_{doc['doc_id']}", use_container_width=True):
                    st.session_state.selected_comparison_doc = doc['doc_id']
                    st.rerun()


def render_document_detail():
    """Render detailed view of a selected document."""
    doc_id = st.session_state.selected_comparison_doc
    
    # Back button
    if st.button("← Back to Document List"):
        st.session_state.selected_comparison_doc = None
        st.session_state.selected_column = None
        st.session_state.selected_group = None
        st.rerun()
    
    st.markdown(f"## 📄 {doc_id}")
    
    # Load comparison data
    with st.spinner("Loading comparison data..."):
        comparison_data = load_comparison_data(doc_id)
        dashboard_data = get_dashboard_report(doc_id)
    
    methods_available = comparison_data.get('methods_available', [])
    method_labels = {
        'gemini_native': 'Gemini',
        'landing_ai_baseline': 'Landing AI',
        'pipeline': 'Pipeline',
        'pipeline_plan_extract': 'Pipeline (plan)',
        'pipeline_keywords': 'Pipeline + KW'
    }
    
    st.caption(f"**Methods:** {', '.join([method_labels.get(m, m) for m in methods_available])}")
    
    # Dashboard cards - show summary stats
    st.markdown("### 📈 Extraction Summary")
    
    by_method = dashboard_data.get('by_method', {})
    
    # Filter to dashboard methods only
    dashboard_methods = ['landing_ai_baseline', 'gemini_native', 'pipeline']
    available_dashboard_methods = [m for m in dashboard_methods if m in by_method]
    
    if available_dashboard_methods:
        cols = st.columns(len(available_dashboard_methods))
        
        for idx, method_name in enumerate(available_dashboard_methods):
            method_stats = by_method[method_name]
            
            with cols[idx]:
                st.metric(
                    label=method_labels.get(method_name, method_name),
                    value=f"{method_stats.get('found', 0)}/{method_stats.get('total', 0)}",
                    delta=f"{method_stats.get('empty', 0)} not found",
                    delta_color="inverse"
                )
                
                empty_groups = method_stats.get('empty_groups', [])
                if empty_groups:
                    with st.expander("Empty groups"):
                        for group in empty_groups[:5]:
                            st.caption(f"• {group}")
    
    st.markdown("---")
    
    # Column Group Selection Section
    st.markdown("""
    <div style="background: linear-gradient(135deg, rgba(28, 214, 206, 0.1) 0%, rgba(49, 225, 247, 0.1) 100%);
                padding: 1.5rem;
                border-radius: 0.75rem;
                border: 1px solid #1CD6CE;
                margin-bottom: 1.5rem;">
        <h4 style="color: #1CD6CE; margin: 0 0 0.5rem 0; font-weight: 600;">
            📂 Column Group Selection
        </h4>
        <p style="color: #31E1F7; margin: 0; font-size: 0.9rem;">
            Select a group to view all columns and compare extraction results
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Column Group Selection Dropdown (instead of sidebar)
    by_group = comparison_data.get('by_group', {})
    groups = sorted(by_group.keys())
    
    if groups:
        col1, col2, col3 = st.columns([4, 1, 1])
        
        with col1:
            # Dropdown for group selection
            group_options = ["-- Select a Column Group --"] + groups
            selected_idx = 0
            if st.session_state.selected_group and st.session_state.selected_group in groups:
                selected_idx = groups.index(st.session_state.selected_group) + 1
            
            selected_group_display = st.selectbox(
                "📁 Select Column Group",
                options=group_options,
                index=selected_idx,
                key="group_selector",
                help="Choose a column group to view its columns"
            )
            
            if selected_group_display != "-- Select a Column Group --":
                if st.session_state.selected_group != selected_group_display:
                    st.session_state.selected_group = selected_group_display
                    st.session_state.selected_column = None
                    st.rerun()
            elif selected_group_display == "-- Select a Column Group --" and st.session_state.selected_group:
                st.session_state.selected_group = None
                st.session_state.selected_column = None
                st.rerun()
        
        with col2:
            # Show column count
            if st.session_state.selected_group:
                columns_in_group = by_group.get(st.session_state.selected_group, [])
                st.metric("Columns", len(columns_in_group))
        
        with col3:
            # Clear selection button
            if st.session_state.selected_group or st.session_state.selected_column:
                st.write("")  # Spacer to align with dropdown
                if st.button("🔄 Clear", use_container_width=True, help="Clear selection"):
                    st.session_state.selected_group = None
                    st.session_state.selected_column = None
                    st.rerun()
    
    # Show current selection breadcrumb
    if st.session_state.selected_group or st.session_state.selected_column:
        breadcrumb = f"📁 {st.session_state.selected_group or 'All Groups'}"
        if st.session_state.selected_column:
            breadcrumb += f" → 📄 {st.session_state.selected_column}"
        
        st.markdown(f"""
        <div style="background-color: #1a2332; 
                    padding: 0.75rem 1rem; 
                    border-radius: 0.5rem; 
                    border-left: 3px solid #31E1F7;
                    margin: 1rem 0;">
            <p style="color: #31E1F7; margin: 0; font-size: 0.9rem; font-weight: 500;">
                {breadcrumb}
            </p>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Layout: Main content and PDF side by side
    col_main, col_right = st.columns([3, 2])
    
    with col_main:
        render_main_content(comparison_data)
    
    with col_right:
        render_pdf_viewer(doc_id)


def render_main_content(comparison_data: Dict[str, Any]):
    """Render main content area."""
    if st.session_state.selected_column:
        render_column_detail(comparison_data)
    elif st.session_state.selected_group:
        render_group_snapshot(comparison_data)
    else:
        st.markdown("""
        <div style="background-color: #1a2332; 
                    padding: 3rem; 
                    border-radius: 0.75rem; 
                    border: 2px dashed #1CD6CE;
                    text-align: center;
                    margin: 2rem 0;">
            <h3 style="color: #1CD6CE; margin-bottom: 1rem;">📁 Get Started</h3>
            <p style="color: #31E1F7; font-size: 1.1rem; margin: 0;">
                Select a column group from the dropdown above to view columns and compare extraction results
            </p>
        </div>
        """, unsafe_allow_html=True)


def render_group_snapshot(comparison_data: Dict[str, Any]):
    """Render snapshot of all columns in a group."""
    group_name = st.session_state.selected_group
    
    # Header with group name
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #1CD6CE 0%, #31E1F7 100%); 
                padding: 1rem 1.5rem; 
                border-radius: 0.75rem; 
                margin-bottom: 1.5rem;">
        <h3 style="color: #000000; margin: 0; font-weight: 700;">📊 {group_name}</h3>
    </div>
    """, unsafe_allow_html=True)
    
    by_group = comparison_data.get('by_group', {})
    rows = by_group.get(group_name, [])
    
    if not rows:
        st.warning(f"No columns found in group: {group_name}")
        return
    
    method_labels = {
        'gemini_native': 'Gemini',
        'landing_ai_baseline': 'Landing AI',
        'pipeline': 'Pipeline',
    }
    
    # Display columns as clickable cards
    st.markdown("""
    <div style="background-color: #1a2332; 
                padding: 1rem; 
                border-radius: 0.5rem; 
                border-left: 3px solid #1CD6CE;
                margin-bottom: 1rem;">
        <p style="color: #1CD6CE; margin: 0; font-weight: 600;">
            👇 Click on any column to view details and PDF evidence
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Create a grid of column buttons
    cols_per_row = 3
    for i in range(0, len(rows), cols_per_row):
        cols = st.columns(cols_per_row)
        
        for idx, row in enumerate(rows[i:i+cols_per_row]):
            if idx < len(cols):
                with cols[idx]:
                    col_name = row.get('column_name', '')
                    methods = row.get('methods', {})
                    
                    # Get value from any method
                    sample_value = "—"
                    value_found = False
                    for method_key in method_labels.keys():
                        method_data = methods.get(method_key, {})
                        val = method_data.get('value', method_data.get('primary_value', ''))
                        if val and val != '—' and val != 'not found' and val.lower() not in ['not found', 'not reported', 'not applicable']:
                            sample_value = val[:35] + '...' if len(val) > 35 else val
                            value_found = True
                            break
                    
                    # Create styled card button with emoji indicator
                    status_emoji = "✅" if value_found else "⚠️"
                    
                    if st.button(
                        f"{status_emoji} {col_name}",
                        key=f"detail_{group_name}_{col_name}",
                        use_container_width=True,
                        help=f"Value: {sample_value}"
                    ):
                        st.session_state.selected_column = col_name
                        st.rerun()
    
    # Also show as table for reference
    st.markdown("---")
    
    with st.expander("📊 View Comparison Table", expanded=False):
        table_data = []
        for row in rows:
            col_name = row.get('column_name', '')
            methods = row.get('methods', {})
            
            row_data = {'Column': col_name}
            
            for method_key, method_label in method_labels.items():
                method_data = methods.get(method_key, {})
                value = method_data.get('value', method_data.get('primary_value', '—'))
                
                # Truncate long values
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + '...'
                
                row_data[method_label] = value
            
            table_data.append(row_data)
        
        # Display as dataframe
        if table_data:
            df = pd.DataFrame(table_data)
            st.dataframe(df, use_container_width=True, height=400)


def render_column_detail(comparison_data: Dict[str, Any]):
    """Render detailed view of a single column."""
    col_name = st.session_state.selected_column
    group_name = st.session_state.selected_group or "Unknown"
    
    # Header with navigation
    col1, col2 = st.columns([4, 1])
    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1CD6CE 0%, #31E1F7 100%); 
                    padding: 1rem 1.5rem; 
                    border-radius: 0.75rem; 
                    margin-bottom: 1rem;">
            <p style="color: #000000; margin: 0; font-size: 0.85rem; font-weight: 500;">
                📁 {group_name}
            </p>
            <h3 style="color: #000000; margin: 0.25rem 0 0 0; font-weight: 700;">
                🔍 {col_name}
            </h3>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Back to group button
        st.write("")  # Spacer
        if st.button("← Back", use_container_width=True, help="Back to group view"):
            st.session_state.selected_column = None
            st.rerun()
    
    # Find the column data
    comparison = comparison_data.get('comparison', [])
    col_row = next((r for r in comparison if r.get('column_name') == col_name), None)
    
    if not col_row:
        st.error("Column data not found")
        return
    
    methods = col_row.get('methods', {})
    
    method_labels = {
        'gemini_native': '🟣 Gemini',
        'landing_ai_baseline': '🟡 Landing AI',
        'pipeline': '🔵 Pipeline',
        'pipeline_plan_extract': '🔵 Pipeline (plan)',
        'pipeline_keywords': '🔵 Pipeline + KW'
    }
    
    # Show each method's result
    for method_key, method_label in method_labels.items():
        if method_key not in methods:
            continue
        
        method_data = methods[method_key]
        
        with st.expander(f"{method_label}", expanded=True):
            value = method_data.get('value', method_data.get('primary_value', 'not found'))
            page = method_data.get('page', 'Unknown')
            source_type = method_data.get('source_type', 'text')
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"**Value:** {value}")
            
            with col2:
                st.markdown(f"**Page:** {page}")
            
            with col3:
                st.markdown(f"**Source:** {source_type}")
            
            # Evidence
            attribution = method_data.get('attribution', {})
            evidence = attribution.get('evidence', '')
            
            if not evidence:
                # Try candidates
                candidates = method_data.get('candidates', [])
                if candidates:
                    evidence = candidates[0].get('evidence', '')
            
            if evidence:
                st.markdown("**Evidence:**")
                st.text_area(
                    "Evidence", 
                    value=evidence, 
                    height=150, 
                    key=f"evidence_{method_key}",
                    label_visibility="collapsed"
                )
            
            # Confidence
            confidence = attribution.get('confidence', 'medium')
            conf_colors = {
                'high': '🟢',
                'medium': '🟡',
                'low': '🔴'
            }
            st.caption(f"Confidence: {conf_colors.get(confidence, '⚪')} {confidence}")


def render_pdf_viewer(doc_id: str):
    """Render PDF viewer with highlights."""
    st.markdown("### 📄 Source in PDF")
    
    if not st.session_state.selected_column:
        st.markdown("""
        <div style="background-color: #1a2332; 
                    padding: 2rem; 
                    border-radius: 0.75rem; 
                    border: 2px dashed #1CD6CE;
                    text-align: center;
                    margin: 2rem 0;">
            <p style="color: #1CD6CE; font-size: 1.1rem; margin: 0;">
                👈 Select a column to view PDF evidence with highlights
            </p>
        </div>
        """, unsafe_allow_html=True)
        return
    
    col_name = st.session_state.selected_column
    
    # Get highlights
    with st.spinner("Loading highlights..."):
        highlights_data = get_highlights_for_column(doc_id, col_name)
    
    if not highlights_data.get('available'):
        st.warning("⚠️ Highlight positions not available for this document")
        return
    
    highlights = highlights_data.get('highlights', [])
    
    if not highlights:
        st.info("ℹ️ No highlights found for this column")
        return
    
    # Display highlight information
    st.success(f"✅ Found {len(highlights)} highlight(s) for **{col_name}**")
    
    # Try to display PDF
    pdf_path = resolve_pdf_path(doc_id)
    
    if not pdf_path or not pdf_path.exists():
        st.warning("⚠️ PDF file not found for this document")
        return
    
    # Try to render with pdf2image (best option with bounding boxes)
    try:
        from pdf2image import convert_from_path
        from PIL import Image, ImageDraw
        
        # Get the page to display (first highlight)
        target_page = highlights[0].get('page', 1)
        
        # Convert PDF page to image
        st.info(f"📄 Rendering page {target_page}...")
        images = convert_from_path(
            pdf_path,
            first_page=target_page,
            last_page=target_page,
            dpi=200  # Higher DPI for better quality
        )
        
        if images:
            img = images[0]
            
            # Draw bounding boxes on image
            draw = ImageDraw.Draw(img, 'RGBA')
            width, height = img.size
            
            for highlight in highlights:
                if highlight.get('page') == target_page:
                    box = highlight.get('box', {})
                    
                    # Convert normalized coordinates to pixels
                    left = int(box.get('left', 0) * width)
                    top = int(box.get('top', 0) * height)
                    right = int(box.get('right', 1) * width)
                    bottom = int(box.get('bottom', 1) * height)
                    
                    # Draw semi-transparent yellow rectangle
                    draw.rectangle(
                        [(left, top), (right, bottom)],
                        fill=(28, 214, 206, 60),  # #1CD6CE with alpha
                        outline=(28, 214, 206, 255),  # Solid border
                        width=3
                    )
            
            # Display the image with highlights
            st.image(img, caption=f"Page {target_page} with highlights", use_column_width=True)
            
            # Show bounding box details
            with st.expander("📍 Highlight Details"):
                for idx, highlight in enumerate(highlights):
                    if highlight.get('page') == target_page:
                        box = highlight.get('box', {})
                        st.markdown(f"""
                        **Highlight {idx + 1}:**
                        - Coordinates: ({box.get('left', 0):.3f}, {box.get('top', 0):.3f}) to ({box.get('right', 0):.3f}, {box.get('bottom', 0):.3f})
                        """)
        
    except ImportError:
        # Fallback: Basic PDF iframe display
        st.warning("⚠️ Install pdf2image and Pillow for enhanced PDF viewing with bounding boxes")
        st.info("Run: `pip install pdf2image Pillow`")
        
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        # Display PDF in iframe
        base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
        target_page = highlights[0].get('page', 1) if highlights else 1
        
        pdf_display = f'''
        <div style="border: 2px solid #1CD6CE; border-radius: 0.75rem; overflow: hidden;">
            <iframe src="data:application/pdf;base64,{base64_pdf}#page={target_page}" 
                    width="100%" height="800" type="application/pdf">
            </iframe>
        </div>
        '''
        
        st.markdown(pdf_display, unsafe_allow_html=True)
        
        # Show highlight positions
        with st.expander("📍 Highlight Positions"):
            for idx, highlight in enumerate(highlights):
                page = highlight.get('page')
                box = highlight.get('box', {})
                st.markdown(f"""
                **Highlight {idx + 1}** (Page {page}):
                - Left: {box.get('left', 0):.3f}, Top: {box.get('top', 0):.3f}
                - Right: {box.get('right', 0):.3f}, Bottom: {box.get('bottom', 0):.3f}
                """)
    
    except Exception as e:
        st.error(f"❌ Error rendering PDF: {str(e)}")
        
    # Download button
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name=f"{doc_id}.pdf",
        mime="application/pdf",
        use_container_width=True
    )


def render_comparison_table_full(comparison_data: Dict[str, Any]):
    """Render full comparison table (alternative view)."""
    st.markdown("### 📊 Full Comparison Table")
    
    comparison = comparison_data.get('comparison', [])
    method_labels = {
        'gemini_native': 'Gemini',
        'landing_ai_baseline': 'Landing AI',
        'pipeline': 'Pipeline',
    }
    
    # Create table data
    table_data = []
    
    for row in comparison:
        col_name = row.get('column_name', '')
        group_name = row.get('group_name', '')
        methods = row.get('methods', {})
        
        row_data = {
            'Column': col_name,
            'Group': group_name,
        }
        
        for method_key, method_label in method_labels.items():
            method_data = methods.get(method_key, {})
            value = method_data.get('value', method_data.get('primary_value', '—'))
            
            # Truncate long values
            if isinstance(value, str) and len(value) > 40:
                value = value[:40] + '...'
            
            row_data[method_label] = value
        
        table_data.append(row_data)
    
    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, height=600)
        
        # Export button
        csv = df.to_csv(index=False)
        st.download_button(
            label="📥 Export Comparison CSV",
            data=csv,
            file_name=f"comparison_{st.session_state.selected_comparison_doc}.csv",
            mime="text/csv"
        )
