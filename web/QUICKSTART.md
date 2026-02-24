# Quick Start Guide - Streamlit Interface

Get up and running with the Streamlit interface in 5 minutes!

## ⚡ Quick Setup

### 1. Install Dependencies

```bash
pip install streamlit pandas python-dotenv google-genai werkzeug
```

Or use the requirements file:

```bash
pip install -r web/streamlit_requirements.txt
```

### 2. Set API Key

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

### 3. Run the App

```bash
# From project root
streamlit run web/streamlit_app.py
```

**Or use the launcher script:**

```bash
bash web/run_streamlit.sh
```

### 4. Open Browser

Navigate to: **http://localhost:8501**

## 🎯 First Extraction

### Option A: Extract from New PDF

1. Click "Browse Files" to upload a PDF
2. Wait for upload to complete
3. Click "🎯 Extract Value"
4. Select a column or enter custom column name
5. Click "Extract Value"
6. View results with page numbers and evidence

### Option B: View Existing Extraction

1. Upload any PDF (just to activate the interface)
2. Click "📋 Extract All Data"
3. Select a document from the dropdown
4. Click "Load Extraction Data"
5. Browse all 133 columns with values

## 📊 Compare Results

1. Click "📊 Compare Extraction Results" in sidebar
2. Browse available documents
3. Click "View Details" on any document
4. Select a column group from sidebar
5. Click on any column to see:
   - Values from multiple methods
   - Evidence and confidence
   - Source in PDF

## 🎨 Interface Features

### Main Page
- **Cards View**: Visual cards for each result
- **Table View**: Compact table view for all results
- **Export**: Download as JSON or CSV

### Comparison Page
- **Group Navigation**: Browse by category
- **Side-by-side Comparison**: See all methods
- **PDF Viewer**: View source with highlights

## 💡 Tips

1. **PDF Size**: Keep PDFs under 50MB for faster upload
2. **Custom Columns**: Use CSV upload for batch custom queries
3. **Evidence**: Expand evidence sections to see reasoning
4. **Export**: Export results before starting new extraction

## ⚙️ Enhanced Features (Optional)

For better PDF highlighting, install:

```bash
pip install pdf2image Pillow
```

This enables:
- Visual highlight overlays on PDF pages
- Better page rendering
- Thumbnail generation

## 🔧 Configuration

### Custom Port

```bash
streamlit run web/streamlit_app.py --server.port 8502
```

### Dark Mode

Streamlit automatically detects your system theme. Toggle in settings menu (☰).

### Memory Settings

For large PDFs, increase memory:

```bash
streamlit run web/streamlit_app.py --server.maxUploadSize 100
```

## 📱 Mobile Access

Access from mobile devices on same network:

```bash
streamlit run web/streamlit_app.py --server.address 0.0.0.0
```

Then open: `http://your-ip:8501`

## ❓ Troubleshooting

### Port Already in Use
```bash
lsof -ti:8501 | xargs kill -9  # Kill existing process
streamlit run web/streamlit_app.py
```

### API Key Error
```bash
# Check if set
echo $GEMINI_API_KEY

# Set it
export GEMINI_API_KEY="your-key"
```

### Import Errors
```bash
# Reinstall dependencies
pip install -r web/streamlit_requirements.txt --upgrade
```

### PDF Not Displaying
- Check browser console for errors
- Try different browser (Chrome/Firefox recommended)
- Enable PDF viewer in browser settings

## 📚 Next Steps

- Read [STREAMLIT_README.md](STREAMLIT_README.md) for detailed documentation
- Explore comparison features with existing extractions
- Customize the interface for your needs
- Add custom visualizations or export formats

## 🎉 You're Ready!

The interface is now running. Upload a PDF and start extracting!

For more details, see the [full documentation](STREAMLIT_README.md).
