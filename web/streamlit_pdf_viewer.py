"""
streamlit_pdf_viewer.py

Enhanced PDF viewer component with highlighting support for Streamlit.
Uses pdf2image for page rendering with highlight overlays.
"""
import streamlit as st
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw
import io


def render_pdf_with_highlights(
    pdf_path: Path,
    highlights: List[Dict[str, Any]],
    page_num: Optional[int] = None,
    width: int = 700
) -> None:
    """
    Render a PDF page with highlight overlays.
    
    Args:
        pdf_path: Path to PDF file
        highlights: List of highlight boxes with 'page' and 'box' keys
        page_num: Specific page to render (if None, uses first highlight page)
        width: Display width in pixels
    """
    if not pdf_path or not pdf_path.exists():
        st.error("PDF file not found")
        return
    
    # Determine page to display
    if page_num is None and highlights:
        page_num = highlights[0].get('page', 1)
    elif page_num is None:
        page_num = 1
    
    try:
        # Try to import pdf2image
        try:
            from pdf2image import convert_from_path
            use_pdf2image = True
        except ImportError:
            use_pdf2image = False
            st.warning("⚠️ pdf2image not installed. Install for better PDF rendering: pip install pdf2image")
        
        if use_pdf2image:
            render_with_pdf2image(pdf_path, highlights, page_num, width)
        else:
            render_basic_pdf(pdf_path, page_num)
            render_highlight_info(highlights, page_num)
    
    except Exception as e:
        st.error(f"Error rendering PDF: {str(e)}")
        render_basic_pdf(pdf_path, page_num)
        render_highlight_info(highlights, page_num)


def render_with_pdf2image(
    pdf_path: Path,
    highlights: List[Dict[str, Any]],
    page_num: int,
    width: int
) -> None:
    """Render PDF page as image with highlight overlays."""
    from pdf2image import convert_from_path
    
    # Convert specific page to image
    images = convert_from_path(
        pdf_path,
        first_page=page_num,
        last_page=page_num,
        dpi=150
    )
    
    if not images:
        st.error(f"Could not render page {page_num}")
        return
    
    img = images[0]
    
    # Filter highlights for this page
    page_highlights = [h for h in highlights if h.get('page') == page_num]
    
    if page_highlights:
        # Draw highlights on image
        img = draw_highlights_on_image(img, page_highlights)
    
    # Display image
    st.image(img, width=width, caption=f"Page {page_num}")
    
    # Show highlight details
    if page_highlights:
        render_highlight_info(page_highlights, page_num)


def draw_highlights_on_image(
    img: Image.Image,
    highlights: List[Dict[str, Any]]
) -> Image.Image:
    """Draw highlight boxes on image."""
    img_with_highlights = img.copy()
    draw = ImageDraw.Draw(img_with_highlights, 'RGBA')
    
    width, height = img.size
    
    for highlight in highlights:
        box = highlight.get('box', {})
        
        # Convert normalized coordinates to pixel coordinates
        left = int(box.get('left', 0) * width)
        top = int(box.get('top', 0) * height)
        right = int(box.get('right', 1) * width)
        bottom = int(box.get('bottom', 1) * height)
        
        # Draw semi-transparent yellow rectangle
        draw.rectangle(
            [(left, top), (right, bottom)],
            fill=(255, 255, 0, 80),  # Yellow with alpha
            outline=(255, 200, 0, 255),  # Orange outline
            width=2
        )
    
    return img_with_highlights


def render_basic_pdf(pdf_path: Path, page_num: int) -> None:
    """Render PDF using basic iframe method."""
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')
    
    pdf_display = f'''
    <iframe src="data:application/pdf;base64,{base64_pdf}#page={page_num}" 
            width="100%" height="800" type="application/pdf">
    </iframe>
    '''
    
    st.markdown(pdf_display, unsafe_allow_html=True)
    
    # Download button
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name=pdf_path.name,
        mime="application/pdf"
    )


def render_highlight_info(highlights: List[Dict[str, Any]], page_num: int) -> None:
    """Render information about highlights."""
    page_highlights = [h for h in highlights if h.get('page') == page_num]
    
    if not page_highlights:
        return
    
    with st.expander(f"📍 Highlight Details ({len(page_highlights)} on this page)"):
        for idx, highlight in enumerate(page_highlights, 1):
            box = highlight.get('box', {})
            st.markdown(f"""
            **Highlight {idx}:**
            - Position: ({box.get('left', 0):.3f}, {box.get('top', 0):.3f}) to 
                       ({box.get('right', 0):.3f}, {box.get('bottom', 0):.3f})
            """)


def render_multi_page_highlights(
    pdf_path: Path,
    highlights: List[Dict[str, Any]],
    width: int = 700
) -> None:
    """Render multiple pages with highlights using tabs."""
    if not highlights:
        st.info("No highlights to display")
        return
    
    # Group highlights by page
    pages_with_highlights = {}
    for highlight in highlights:
        page = highlight.get('page', 1)
        if page not in pages_with_highlights:
            pages_with_highlights[page] = []
        pages_with_highlights[page].append(highlight)
    
    # Create tabs for each page
    page_numbers = sorted(pages_with_highlights.keys())
    
    if len(page_numbers) == 1:
        # Single page - no tabs needed
        render_pdf_with_highlights(
            pdf_path,
            highlights,
            page_num=page_numbers[0],
            width=width
        )
    else:
        # Multiple pages - use tabs
        tab_labels = [f"Page {p}" for p in page_numbers]
        tabs = st.tabs(tab_labels)
        
        for tab, page_num in zip(tabs, page_numbers):
            with tab:
                page_highlights = pages_with_highlights[page_num]
                render_pdf_with_highlights(
                    pdf_path,
                    page_highlights,
                    page_num=page_num,
                    width=width
                )


def create_pdf_thumbnail(pdf_path: Path, page_num: int = 1, size: tuple = (200, 280)) -> Optional[Image.Image]:
    """Create a thumbnail image of a PDF page."""
    try:
        from pdf2image import convert_from_path
        
        images = convert_from_path(
            pdf_path,
            first_page=page_num,
            last_page=page_num,
            dpi=72
        )
        
        if images:
            img = images[0]
            img.thumbnail(size, Image.Resampling.LANCZOS)
            return img
    
    except Exception:
        pass
    
    return None
