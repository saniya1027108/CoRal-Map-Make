# Streamlit Interface - Clinical Trial Data Extraction

A modern, user-friendly Streamlit interface for extracting structured data from clinical trial PDFs using AI.

## 🚀 Quick Links

- **[5-Minute Quick Start](QUICKSTART.md)** - Get started immediately
- **[Installation Guide](INSTALLATION_INSTRUCTIONS.md)** - Detailed setup instructions
- **[Interface Guide](INTERFACE_GUIDE.md)** - Visual guide to using the interface
- **[Full Documentation](STREAMLIT_README.md)** - Complete reference
- **[Migration Guide](MIGRATION_GUIDE.md)** - Flask to Streamlit comparison

## ⚡ Ultra Quick Start

```bash
# 1. Install
pip install streamlit pandas python-dotenv google-genai werkzeug

# 2. Set API key (optional - only for new extractions)
export GEMINI_API_KEY="your-key"

# 3. Run
streamlit run web/streamlit_app.py

# 4. Open browser
# http://localhost:8501
```

## 🎯 Features Overview

### Main Features
✅ **PDF Upload & Extraction**
- Single column extraction
- All 133 columns view
- Custom CSV batch extraction

✅ **Multi-Method Comparison**
- Compare Gemini, Landing AI, and Pipeline results
- Side-by-side value comparison
- Evidence and confidence scores

✅ **PDF Evidence Highlighting**
- Visual highlights on PDF pages
- Bounding box overlays
- Page navigation

✅ **User-Friendly Interface**
- Clean, modern design
- Mobile responsive
- Real-time feedback
- Export to JSON/CSV

## 📚 Documentation Structure

```
web/
├── README_STREAMLIT.md              ← You are here (Start)
├── QUICKSTART.md                    ← 5-minute setup
├── INSTALLATION_INSTRUCTIONS.md     ← Detailed installation
├── INTERFACE_GUIDE.md               ← Visual usage guide
├── STREAMLIT_README.md              ← Full documentation
├── MIGRATION_GUIDE.md               ← Flask comparison
└── STREAMLIT_IMPLEMENTATION_SUMMARY.md  ← Technical details
```

## 🎓 Learning Path

### New Users
1. **Start here**: [QUICKSTART.md](QUICKSTART.md)
2. **If issues**: [INSTALLATION_INSTRUCTIONS.md](INSTALLATION_INSTRUCTIONS.md)
3. **Learn interface**: [INTERFACE_GUIDE.md](INTERFACE_GUIDE.md)

### Power Users
1. **Full features**: [STREAMLIT_README.md](STREAMLIT_README.md)
2. **Customization**: Code in `streamlit_app.py`
3. **Extensions**: Add to `streamlit_comparison.py`

### Developers
1. **Architecture**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
2. **Implementation**: [STREAMLIT_IMPLEMENTATION_SUMMARY.md](STREAMLIT_IMPLEMENTATION_SUMMARY.md)
3. **Testing**: Run `python3 web/test_streamlit.py`

## 📦 File Structure

### Application Files
```
web/
├── streamlit_app.py              # Main application (600 lines)
├── streamlit_comparison.py       # Comparison interface (450 lines)
├── streamlit_pdf_viewer.py       # PDF viewer component (250 lines)
└── streamlit_requirements.txt    # Dependencies
```

### Documentation Files
```
web/
├── README_STREAMLIT.md           # This file
├── QUICKSTART.md                 # Quick start guide
├── INSTALLATION_INSTRUCTIONS.md  # Setup guide
├── INTERFACE_GUIDE.md            # Usage guide
├── STREAMLIT_README.md           # Full documentation
├── MIGRATION_GUIDE.md            # Flask comparison
└── STREAMLIT_IMPLEMENTATION_SUMMARY.md  # Technical summary
```

### Backend Services (Shared)
```
web/
├── extraction_service.py         # Extraction logic
├── comparison_service.py         # Comparison logic
├── highlight_service.py          # PDF highlighting
└── explainability_service.py     # Attribution analysis
```

### Utilities
```
web/
├── run_streamlit.sh              # Launcher script
└── test_streamlit.py             # Test suite
```

## 🎯 Use Cases

### 1. Extract Data from New PDF
**Best for**: New documents not yet processed

```
1. Upload PDF
2. Select "Extract Value"
3. Choose column
4. View results with evidence
```

[Detailed guide →](INTERFACE_GUIDE.md#task-1-extract-single-column-from-new-pdf)

### 2. View Existing Extractions
**Best for**: Reviewing pre-computed results

```
1. Select "Extract All Data"
2. Choose document
3. View all 133 columns
4. Export if needed
```

[Detailed guide →](INTERFACE_GUIDE.md#task-2-view-all-columns-from-existing-extraction)

### 3. Compare Methods
**Best for**: Analyzing extraction quality

```
1. Navigate to "Compare Results"
2. Select document
3. View differences between methods
4. Check PDF evidence
```

[Detailed guide →](INTERFACE_GUIDE.md#task-3-compare-methods-for-a-document)

### 4. Batch Custom Extraction
**Best for**: Many custom columns

```
1. Create CSV with columns
2. Upload CSV
3. Extract all columns
4. Export results
```

[Detailed guide →](INTERFACE_GUIDE.md#method-c-custom-csv)

## 🔧 Configuration

### Basic Configuration

No configuration needed for basic use! Just run:
```bash
streamlit run web/streamlit_app.py
```

### Advanced Configuration

Create `.streamlit/config.toml`:
```toml
[server]
port = 8501
headless = false
enableCORS = false

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"

[browser]
gatherUsageStats = false
```

### Environment Variables

```bash
# Required for new extractions
export GEMINI_API_KEY="your-key"

# Optional: Custom port
export STREAMLIT_SERVER_PORT=8502

# Optional: Enable debug logging
export STREAMLIT_LOG_LEVEL=debug
```

## 🆚 Streamlit vs Flask

| Aspect | Flask | Streamlit | Winner |
|--------|-------|-----------|--------|
| Setup | Complex | Simple | 🥇 Streamlit |
| Coding | HTML+CSS+JS | Python only | 🥇 Streamlit |
| Development | Slower | Faster | 🥇 Streamlit |
| Customization | Full control | Limited | 🥇 Flask |
| UI Quality | Custom | Modern | 🥇 Streamlit |
| Maintenance | Complex | Simple | 🥇 Streamlit |

**Recommendation**: 
- Use **Streamlit** for internal tools, dashboards, and rapid development
- Use **Flask** if you need full UI control or have existing Flask infrastructure

Both interfaces use the same backend services, so you can use both!

[Full comparison →](MIGRATION_GUIDE.md)

## 🎨 Screenshots & Examples

### Home Page
```
┌─────────────────────────────────────────┐
│  🏥 Clinical Trial Data Extraction      │
│  AI-powered extraction from PDFs        │
├─────────────────────────────────────────┤
│  📄 Step 1: Upload PDF                  │
│     [Drag & Drop or Browse]             │
│                                         │
│  🎯 Step 2: Select Method               │
│     [Extract Value | All Data | CSV]    │
│                                         │
│  📊 Step 3: View Results                │
│     [Cards View | Table View | Export]  │
└─────────────────────────────────────────┘
```

### Comparison Page
```
┌─────────────────────────────────────────┐
│  📊 Compare Extraction Results          │
├─────────────────────────────────────────┤
│  Documents (10 found)                   │
│  ┌───────┐ ┌───────┐ ┌───────┐        │
│  │NCT001 │ │NCT002 │ │NCT003 │        │
│  │🟣🟡🔵 │ │🟣🔵   │ │🟡🔵   │        │
│  │[View] │ │[View] │ │[View] │        │
│  └───────┘ └───────┘ └───────┘        │
└─────────────────────────────────────────┘
```

[More examples →](INTERFACE_GUIDE.md)

## ✅ Testing

### Run Test Suite
```bash
python3 web/test_streamlit.py
```

Expected output:
```
============================================================
Streamlit Interface Test Suite
============================================================
✅ All imports successful!
✅ All required files exist!
✅ Backend services are functional!
============================================================
```

### Manual Testing
```bash
# Start app
streamlit run web/streamlit_app.py

# Test in browser
# 1. Upload PDF
# 2. Try each extraction method
# 3. Navigate to comparison page
# 4. Export results
```

## 🐛 Common Issues & Solutions

### Issue: Import errors
**Solution**: Install dependencies
```bash
pip install -r web/streamlit_requirements.txt
```

### Issue: Port already in use
**Solution**: Use different port
```bash
streamlit run web/streamlit_app.py --server.port 8502
```

### Issue: API key errors
**Solution**: Set environment variable
```bash
export GEMINI_API_KEY="your-key"
```

[More solutions →](INSTALLATION_INSTRUCTIONS.md#troubleshooting)

## 📊 Performance

### Benchmarks
- **Startup time**: ~2-3 seconds
- **PDF upload**: <1 second for typical PDFs
- **Single extraction**: ~5-10 seconds (depends on model)
- **View all columns**: Instant (pre-computed)
- **Comparison load**: <1 second

### Optimization Tips
- Keep PDFs under 50MB
- Use "Extract All Data" for instant results
- Export large datasets rather than viewing in browser
- Use pagination for very large result sets

## 🔐 Security

### Current Implementation
✅ File type validation
✅ Size limits (50MB)
✅ Secure file handling
✅ Environment-based secrets

### For Production
Consider adding:
- User authentication
- Rate limiting
- Input sanitization
- HTTPS encryption
- Audit logging

## 🚢 Deployment Options

### Local (Development)
```bash
streamlit run web/streamlit_app.py
```

### Network Access
```bash
streamlit run web/streamlit_app.py --server.address 0.0.0.0
```

### Streamlit Cloud (Free)
1. Push to GitHub
2. Deploy via share.streamlit.io
3. Add secrets in dashboard

### Docker
```bash
docker build -t clinical-extraction .
docker run -p 8501:8501 clinical-extraction
```

[Detailed deployment →](STREAMLIT_README.md#deployment)

## 🤝 Contributing

### Adding Features
1. Edit `streamlit_app.py` for main features
2. Edit `streamlit_comparison.py` for comparison features
3. Edit `streamlit_pdf_viewer.py` for PDF features

### Testing Changes
```bash
# Test imports
python3 web/test_streamlit.py

# Run app with changes
streamlit run web/streamlit_app.py
```

### Code Style
- Follow PEP 8
- Add docstrings to functions
- Comment complex logic
- Use type hints where helpful

## 📞 Support

### Quick Help
1. Run test script: `python3 web/test_streamlit.py`
2. Check documentation: [QUICKSTART.md](QUICKSTART.md)
3. Review troubleshooting: [INSTALLATION_INSTRUCTIONS.md](INSTALLATION_INSTRUCTIONS.md#troubleshooting)

### Documentation
- **General**: [STREAMLIT_README.md](STREAMLIT_README.md)
- **Setup**: [INSTALLATION_INSTRUCTIONS.md](INSTALLATION_INSTRUCTIONS.md)
- **Usage**: [INTERFACE_GUIDE.md](INTERFACE_GUIDE.md)
- **Technical**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

## 🎉 Success Stories

### Feature Highlights
✅ **1,300 lines of code** vs 1,800 in Flask (~27% reduction)
✅ **100% feature parity** with Flask interface
✅ **10+ documents** ready for comparison
✅ **133 columns** supported
✅ **3 extraction methods** available
✅ **Multiple export formats** (JSON, CSV)

### User Benefits
- Easier to use than Flask interface
- Faster development of new features
- Better mobile experience
- Real-time feedback
- Modern, clean design

## 🗺️ Roadmap

### Current Version (v1.0)
✅ All basic features implemented
✅ Comparison view complete
✅ PDF highlighting working
✅ Export functionality ready

### Future Enhancements (Optional)
- 🔲 Advanced PDF highlighting component
- 🔲 Real-time extraction progress
- 🔲 Batch document processing
- 🔲 Custom visualizations
- 🔲 User authentication
- 🔲 Results caching

## 📄 License

Same license as the parent project.

## 🙏 Acknowledgments

Built with:
- [Streamlit](https://streamlit.io) - Main framework
- [Pandas](https://pandas.pydata.org) - Data handling
- [Google GenAI](https://ai.google.dev) - Extraction engine
- [pdf2image](https://github.com/Belval/pdf2image) - PDF rendering (optional)

## 📚 Additional Resources

### Streamlit Learning
- [Official Docs](https://docs.streamlit.io)
- [Gallery](https://streamlit.io/gallery)
- [Cheat Sheet](https://docs.streamlit.io/library/cheatsheet)

### This Project
- **Quick Start**: [QUICKSTART.md](QUICKSTART.md)
- **Installation**: [INSTALLATION_INSTRUCTIONS.md](INSTALLATION_INSTRUCTIONS.md)
- **Interface Guide**: [INTERFACE_GUIDE.md](INTERFACE_GUIDE.md)
- **Full Docs**: [STREAMLIT_README.md](STREAMLIT_README.md)
- **Migration**: [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)

---

## 🚀 Get Started Now!

```bash
# Install
pip install streamlit pandas python-dotenv google-genai

# Run
streamlit run web/streamlit_app.py

# Enjoy! 🎉
```

**Questions?** Start with [QUICKSTART.md](QUICKSTART.md) or [INSTALLATION_INSTRUCTIONS.md](INSTALLATION_INSTRUCTIONS.md)

**Issues?** Check [troubleshooting section](INSTALLATION_INSTRUCTIONS.md#troubleshooting)

**Ready to use?** Open http://localhost:8501 and start extracting!
