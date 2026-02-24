# Clinical Trial Data Extraction - Streamlit Interface

A user-friendly Streamlit interface for extracting structured data from clinical trial PDFs using AI.

## 🎯 Features

### 1. **PDF Upload & Extraction**
- Upload PDF documents (up to 50MB)
- Three extraction modes:
  - **Extract Value**: Extract a single column value
  - **Extract All Data**: View complete 133-column extraction data
  - **Custom CSV**: Upload CSV with custom queries

### 2. **Results Visualization**
- View results in card or table format
- See extracted values with:
  - Page numbers
  - Modality (text/table/figure)
  - Evidence/attribution
- Export results to JSON or CSV

### 3. **Multi-Method Comparison**
- Compare extraction results across multiple methods:
  - Gemini Native
  - Landing AI Baseline
  - Pipeline (various configurations)
- View differences and agreements
- Filter by column groups

### 4. **PDF Evidence Highlighting**
- View source PDF with highlighted regions
- See exact location where values were extracted
- Bounding box visualization for attribution

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Streamlit and required packages
pip install -r web/streamlit_requirements.txt

# Or install with your existing requirements
pip install streamlit pandas python-dotenv google-genai werkzeug
```

### 2. Set Environment Variables

```bash
# Set your Gemini API key
export GEMINI_API_KEY="your-api-key-here"
```

### 3. Run the Application

```bash
# From the project root directory
streamlit run web/streamlit_app.py

# Or with custom port
streamlit run web/streamlit_app.py --server.port 8501
```

### 4. Open in Browser

The application will automatically open in your browser at:
```
http://localhost:8501
```

## 📖 Usage Guide

### Extraction Workflow

#### Option 1: Extract Single Column
1. Upload a PDF file
2. Select "Extract Value"
3. Choose a column from the dropdown or enter a custom column name
4. Click "Extract Value"
5. View results with evidence and page numbers

#### Option 2: Extract All Data
1. Upload a PDF file
2. Select "Extract All Data"
3. Choose a document from existing extractions
4. Click "Load Extraction Data"
5. View all 133 columns with their values

#### Option 3: Custom CSV Query
1. Upload a PDF file
2. Select "Custom CSV"
3. Upload a CSV file with columns: `column_name` and `definition`
4. Click "Extract from CSV"
5. View extraction results for all custom columns

### Comparison Workflow

1. Navigate to "Compare Extraction Results" page
2. Browse available documents with extraction results
3. Click "View Details" on any document
4. Explore column groups in the sidebar
5. Click on a group to see all columns
6. Click "Details" on any column to see:
   - Values from each method
   - Evidence and confidence scores
   - PDF source with highlights

## 🎨 Interface Features

### Main Extraction Page
- **Step-by-step workflow**: Guided process from upload to results
- **Multiple view modes**: Cards or table view for results
- **Export options**: Download results as JSON or CSV
- **Real-time feedback**: Progress indicators and status messages

### Comparison Page
- **Document browser**: Grid view of all available documents
- **Group navigation**: Organized by clinical trial data categories
- **Side-by-side comparison**: See results from multiple methods
- **PDF viewer**: Embedded viewer with highlight overlay
- **Search and filter**: Find specific documents or columns

## 📁 Project Structure

```
web/
├── streamlit_app.py           # Main Streamlit application
├── streamlit_comparison.py    # Comparison interface module
├── streamlit_requirements.txt # Streamlit dependencies
├── extraction_service.py      # Backend extraction service
├── comparison_service.py      # Comparison data service
├── highlight_service.py       # PDF highlighting service
├── explainability_service.py  # Attribution analysis service
└── uploads/                   # Temporary PDF storage
```

## 🔧 Configuration

### Streamlit Configuration (Optional)

Create `.streamlit/config.toml` in your project root:

```toml
[server]
port = 8501
headless = true
enableCORS = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[browser]
gatherUsageStats = false
```

### API Keys

The application requires a Gemini API key for extraction:

```bash
# Set in environment
export GEMINI_API_KEY="your-api-key"

# Or create .env file
echo "GEMINI_API_KEY=your-api-key" > .env
```

## 📊 Data Sources

### Extraction Results
The comparison feature loads pre-computed extraction results from:

- `experiment-scripts/baselines_file_search_results/gemini_native/`
- `experiment-scripts/baseline_landing_ai_w_gemini/results/`
- `new_pipeline_outputs/results/`

### Column Definitions
- `src/table_definitions/Definitions_open_ended.csv`
- `src/table_definitions/Definitions_with_eval_category.csv`

## 🆚 Comparison with Flask App

### Advantages of Streamlit Interface

✅ **Easier to Use**
- No need to understand HTML/CSS/JavaScript
- Intuitive navigation and controls
- Better mobile responsiveness

✅ **Better Interactivity**
- Real-time updates and feedback
- Integrated widgets (file upload, selectboxes, etc.)
- Smooth state management

✅ **Cleaner Code**
- Python-only (no need for templates or static files)
- Less boilerplate code
- Easier to maintain and extend

✅ **Better Data Visualization**
- Built-in dataframe display
- Expandable sections
- Metrics and charts

✅ **Rapid Development**
- Faster to add new features
- No need to write frontend code
- Auto-reload on code changes

### Feature Parity

| Feature | Flask App | Streamlit App |
|---------|-----------|---------------|
| PDF Upload | ✅ | ✅ |
| Single Column Extraction | ✅ | ✅ |
| All Columns Extraction | ✅ | ✅ |
| Custom CSV Extraction | ✅ | ✅ |
| Results Display | ✅ | ✅ Enhanced |
| Export JSON/CSV | ✅ | ✅ |
| Multi-Method Comparison | ✅ | ✅ |
| PDF Highlighting | ✅ | ✅ Limited* |
| Group Navigation | ✅ | ✅ |
| Column Detail View | ✅ | ✅ |

*Note: PDF highlighting in Streamlit uses iframe display with page navigation. Full bounding box overlay requires custom JavaScript component (can be added as enhancement).

## 🔄 Migration from Flask

To fully migrate from Flask to Streamlit:

1. **Current State**: Both interfaces work independently
2. **Shared Backend**: Both use the same service modules
3. **Choose Your Interface**:
   - Use Streamlit for better UX and easier maintenance
   - Keep Flask if you need custom frontend control

## 🛠️ Troubleshooting

### Issue: "GEMINI_API_KEY not set"
**Solution**: Set the environment variable before running:
```bash
export GEMINI_API_KEY="your-key"
streamlit run web/streamlit_app.py
```

### Issue: "No documents found in comparison"
**Solution**: Run some extractions first using the pipeline or baseline scripts to generate results in the expected directories.

### Issue: "PDF not displaying"
**Solution**: Check that the PDF file exists in the dataset folder or pipeline outputs. Some browsers may block iframe PDF display.

### Issue: Port already in use
**Solution**: Use a different port:
```bash
streamlit run web/streamlit_app.py --server.port 8502
```

## 📝 Development

### Adding New Features

1. **New Extraction Method**: Extend `extraction_service.py`
2. **New Comparison View**: Add functions to `streamlit_comparison.py`
3. **Custom Visualizations**: Use Streamlit's built-in charts or integrate with Plotly

### Testing

```bash
# Run the app in development mode
streamlit run web/streamlit_app.py --server.runOnSave true
```

## 📄 License

Same license as the parent project.

## 🤝 Contributing

Improvements and bug fixes welcome! The Streamlit interface is designed to be easy to extend.

## 📞 Support

For issues or questions, refer to the main project documentation or open an issue.
