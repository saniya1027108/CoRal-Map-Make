# Installation Instructions - Streamlit Interface

Complete step-by-step instructions to get the Streamlit interface running.

## ✅ Prerequisites

Before starting, ensure you have:
- Python 3.8 or higher
- pip package manager
- Access to the project repository
- (Optional) GEMINI_API_KEY for new extractions

## 📦 Installation Steps

### Step 1: Verify Project Structure

Check that you're in the project root:
```bash
cd /mnt/data1/smulla1/mayo_new
pwd  # Should show: /mnt/data1/smulla1/mayo_new
```

Verify Streamlit files exist:
```bash
ls -la web/streamlit_*.py
# Should show:
#   web/streamlit_app.py
#   web/streamlit_comparison.py
#   web/streamlit_pdf_viewer.py
```

### Step 2: Install Dependencies

Install Streamlit and required packages:

```bash
pip install streamlit pandas python-dotenv google-genai werkzeug
```

Or use the requirements file:

```bash
pip install -r web/streamlit_requirements.txt
```

Expected output:
```
Collecting streamlit>=1.28.0
  Downloading streamlit-1.xx.x.tar.gz
Collecting pandas>=2.0.0
  Downloading pandas-2.x.x.tar.gz
...
Successfully installed streamlit-1.xx.x pandas-2.x.x ...
```

### Step 3: Install Optional Dependencies (Recommended)

For enhanced PDF rendering with visual highlights:

```bash
pip install pdf2image Pillow
```

**Note**: This also requires `poppler-utils` system package:

```bash
# On Ubuntu/Debian
sudo apt-get install poppler-utils

# On macOS (with Homebrew)
brew install poppler

# On Windows
# Download from: http://blog.alivate.com.au/poppler-windows/
```

### Step 4: Set Environment Variables

Set your Gemini API key (required for new extractions):

```bash
export GEMINI_API_KEY="your-gemini-api-key-here"
```

To make it permanent, add to your `~/.bashrc` or `~/.bash_profile`:

```bash
echo 'export GEMINI_API_KEY="your-key"' >> ~/.bashrc
source ~/.bashrc
```

Or create a `.env` file in the project root:

```bash
echo "GEMINI_API_KEY=your-key" > .env
```

### Step 5: Verify Installation

Run the test script:

```bash
python3 web/test_streamlit.py
```

Expected output:
```
============================================================
Streamlit Interface Test Suite
============================================================
Testing imports...
  ✓ streamlit
  ✓ pandas
  ✓ extraction_service
  ✓ comparison_service
  ✓ highlight_service

✅ All imports successful!

Testing file structure...
  ✓ web/streamlit_app.py
  ✓ web/streamlit_comparison.py
  ...

✅ All required files exist!

Testing backend services...
  ✓ Found 10 documents with extraction results
  ✓ Loaded 133 column definitions

✅ Backend services are functional!

============================================================
✅ All tests passed!

You can now run the Streamlit app:
  streamlit run web/streamlit_app.py
============================================================
```

## 🚀 Running the Application

### Option 1: Direct Command

```bash
streamlit run web/streamlit_app.py
```

### Option 2: Launcher Script

```bash
bash web/run_streamlit.sh
```

### Option 3: Custom Port

```bash
streamlit run web/streamlit_app.py --server.port 8502
```

### Option 4: Network Access

To access from other devices on your network:

```bash
streamlit run web/streamlit_app.py --server.address 0.0.0.0
```

Then access from other devices using: `http://your-ip-address:8501`

## 🌐 Accessing the Interface

After running the command, Streamlit will:
1. Start the server
2. Automatically open your default browser
3. Navigate to `http://localhost:8501`

If the browser doesn't open automatically, manually navigate to:
```
http://localhost:8501
```

## ✅ Verification Checklist

Check that everything is working:

- [ ] Test script passes all tests
- [ ] Streamlit app starts without errors
- [ ] Browser opens to interface
- [ ] You see "Clinical Trial Data Extraction" header
- [ ] Sidebar shows navigation options
- [ ] Can upload a PDF file
- [ ] Extraction methods are selectable
- [ ] Comparison page loads document list

## 🔧 Troubleshooting

### Issue 1: "streamlit: command not found"

**Problem**: Streamlit not in PATH
**Solution**:
```bash
pip install --user streamlit
# or
pip3 install streamlit
```

### Issue 2: "No module named 'streamlit'"

**Problem**: Package not installed correctly
**Solution**:
```bash
pip uninstall streamlit
pip install streamlit --upgrade
```

### Issue 3: "Port 8501 is already in use"

**Problem**: Another process using port
**Solution**:
```bash
# Find and kill process
lsof -ti:8501 | xargs kill -9

# Or use different port
streamlit run web/streamlit_app.py --server.port 8502
```

### Issue 4: "GEMINI_API_KEY not set"

**Problem**: API key not configured
**Solution**:
```bash
export GEMINI_API_KEY="your-key"
# or
echo "GEMINI_API_KEY=your-key" > .env
```

**Note**: API key is only required for NEW extractions. You can still:
- View existing extraction results
- Use comparison features
- Browse all interface features

### Issue 5: "Import error: google.genai"

**Problem**: google-genai not installed
**Solution**:
```bash
pip install google-genai --upgrade
```

### Issue 6: Browser doesn't open

**Problem**: Streamlit can't open browser automatically
**Solution**: Manually navigate to `http://localhost:8501`

### Issue 7: "Permission denied" errors

**Problem**: No write access to uploads directory
**Solution**:
```bash
mkdir -p web/uploads
chmod 755 web/uploads
```

### Issue 8: Import errors for project modules

**Problem**: Python path not configured
**Solution**: Run from project root:
```bash
cd /mnt/data1/smulla1/mayo_new
streamlit run web/streamlit_app.py
```

## 🐍 Python Version Issues

### Check Python Version

```bash
python3 --version
# Should show: Python 3.8.x or higher
```

### If Python is too old

```bash
# Install newer Python (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3.10

# Use specific version
python3.10 -m pip install streamlit
python3.10 -m streamlit run web/streamlit_app.py
```

## 📦 Virtual Environment (Recommended)

For better dependency isolation:

### Create Virtual Environment

```bash
cd /mnt/data1/smulla1/mayo_new
python3 -m venv venv
source venv/bin/activate
```

### Install Dependencies

```bash
pip install -r web/streamlit_requirements.txt
```

### Run Application

```bash
streamlit run web/streamlit_app.py
```

### Deactivate When Done

```bash
deactivate
```

## 🐳 Docker Installation (Alternative)

If you prefer Docker:

### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

# Copy project files
COPY . /app

# Install dependencies
RUN pip install -r web/streamlit_requirements.txt

# Expose Streamlit port
EXPOSE 8501

# Run Streamlit
CMD ["streamlit", "run", "web/streamlit_app.py", "--server.address", "0.0.0.0"]
```

### Build and Run

```bash
docker build -t clinical-trial-extraction .
docker run -p 8501:8501 -e GEMINI_API_KEY="your-key" clinical-trial-extraction
```

Access at: `http://localhost:8501`

## ☁️ Cloud Deployment

### Streamlit Cloud (Free)

1. Push code to GitHub
2. Visit https://share.streamlit.io
3. Connect repository
4. Select `web/streamlit_app.py` as main file
5. Add secrets (GEMINI_API_KEY)
6. Deploy!

### Heroku

```bash
# Install Heroku CLI
# Create Procfile:
echo "web: streamlit run web/streamlit_app.py --server.port $PORT" > Procfile

# Deploy
heroku create
heroku config:set GEMINI_API_KEY="your-key"
git push heroku main
```

## 🔍 Verification Commands

### Quick Test

```bash
# Test imports
python3 -c "import streamlit; print('Streamlit:', streamlit.__version__)"

# Test app loads
streamlit run web/streamlit_app.py --server.headless true &
sleep 5
curl http://localhost:8501
kill %1
```

### Full Test

```bash
python3 web/test_streamlit.py
```

## 📊 System Requirements

### Minimum Requirements
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 500 MB free space
- **Python**: 3.8+
- **OS**: Linux, macOS, or Windows

### Recommended Requirements
- **CPU**: 4+ cores
- **RAM**: 8 GB
- **Disk**: 2 GB free space
- **Python**: 3.10+
- **Browser**: Chrome or Firefox (latest)

## 🎓 Post-Installation

### Next Steps

1. **Verify Everything Works**:
   ```bash
   python3 web/test_streamlit.py
   ```

2. **Read Quick Start**:
   ```bash
   cat web/QUICKSTART.md
   ```

3. **Try First Extraction**:
   - Upload a PDF
   - Extract a column
   - View results

4. **Explore Comparison**:
   - Navigate to comparison page
   - Select a document
   - View different methods

### Learning Resources

- **Quick Start**: `web/QUICKSTART.md` (5 minutes)
- **Full Documentation**: `web/STREAMLIT_README.md` (comprehensive)
- **Interface Guide**: `web/INTERFACE_GUIDE.md` (visual guide)
- **Migration Guide**: `web/MIGRATION_GUIDE.md` (Flask comparison)

### Getting Help

1. Run test script: `python3 web/test_streamlit.py`
2. Check browser console (F12) for errors
3. Review troubleshooting section above
4. Check Streamlit docs: https://docs.streamlit.io

## ✅ Success Indicators

You know installation was successful when:

✅ Test script passes all tests
✅ `streamlit run` starts without errors
✅ Browser shows interface at http://localhost:8501
✅ Can navigate between Home and Compare pages
✅ Can upload files
✅ Can view existing extraction results

## 🎉 You're Ready!

If all steps completed successfully, you can now:

- ✅ Extract data from PDFs
- ✅ View existing extraction results
- ✅ Compare results across methods
- ✅ Export data to JSON/CSV
- ✅ View PDF evidence with highlights

Enjoy using the Clinical Trial Data Extraction Streamlit interface!

---

**Installation Support**: For issues not covered here, check the full documentation in `web/STREAMLIT_README.md`
