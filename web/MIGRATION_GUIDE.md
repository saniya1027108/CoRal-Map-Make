# Migration Guide: Flask to Streamlit

This guide helps you understand the differences and migrate from the Flask interface to Streamlit.

## 📋 Overview

Both interfaces provide the same functionality but with different approaches:

- **Flask**: Traditional web framework with HTML templates and JavaScript
- **Streamlit**: Modern Python-only framework with reactive updates

## 🔄 Architecture Comparison

### Flask Architecture

```
Flask App (main_app.py)
├── Templates (HTML/CSS/JS)
│   ├── index.html
│   └── comparison.html
├── Static Files
│   ├── css/styles.css
│   ├── js/app.js
│   └── js/comparison.js
└── Backend Services
    ├── extraction_service.py
    ├── comparison_service.py
    ├── highlight_service.py
    └── explainability_service.py
```

### Streamlit Architecture

```
Streamlit App (streamlit_app.py)
├── Main Interface (Python only)
│   ├── streamlit_app.py
│   └── streamlit_comparison.py
├── Enhanced Components (Optional)
│   └── streamlit_pdf_viewer.py
└── Shared Backend Services
    ├── extraction_service.py
    ├── comparison_service.py
    ├── highlight_service.py
    └── explainability_service.py
```

## 📊 Feature Comparison Matrix

| Feature | Flask | Streamlit | Notes |
|---------|-------|-----------|-------|
| **Setup Complexity** | ⭐⭐⭐ | ⭐ | Streamlit: pip install + run |
| **Code Maintainability** | ⭐⭐ | ⭐⭐⭐⭐⭐ | Pure Python vs HTML/CSS/JS |
| **Development Speed** | ⭐⭐ | ⭐⭐⭐⭐⭐ | No frontend coding needed |
| **UI Customization** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Flask: Full control, Streamlit: Limited |
| **Real-time Updates** | ⭐⭐ | ⭐⭐⭐⭐⭐ | Streamlit: Built-in reactivity |
| **State Management** | ⭐⭐ | ⭐⭐⭐⭐ | Streamlit: session_state |
| **PDF Highlighting** | ⭐⭐⭐⭐ | ⭐⭐⭐ | Flask: Custom JS, Streamlit: Limited |
| **Mobile Responsive** | ⭐⭐⭐ | ⭐⭐⭐⭐ | Streamlit: Auto-responsive |
| **Production Ready** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Both suitable |
| **Learning Curve** | ⭐⭐⭐⭐ | ⭐⭐ | Streamlit: Easier to learn |

## 🔀 Code Comparison

### PDF Upload

**Flask:**
```python
@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({"success": False, "error": "No file provided"}), 400
    
    file = request.files['file']
    filename = secure_filename(file.filename)
    filepath = app.config['UPLOAD_FOLDER'] / filename
    file.save(str(filepath))
    
    service = get_extraction_service()
    result = service.upload_pdf(str(filepath))
    return jsonify(result), 200
```

**Streamlit:**
```python
uploaded_file = st.file_uploader("Choose a PDF file", type=['pdf'])

if uploaded_file is not None:
    pdf_path = upload_dir / uploaded_file.name
    with open(pdf_path, 'wb') as f:
        f.write(uploaded_file.getbuffer())
    
    service = get_extraction_service()
    result = service.upload_pdf(str(pdf_path))
    
    if result.get('success'):
        st.success("✓ PDF Loaded Successfully")
```

### Results Display

**Flask:**
```javascript
// app.js
function displayResults(results) {
    const container = document.getElementById('results-container');
    container.innerHTML = '';
    
    for (const [colName, colData] of Object.entries(results)) {
        const card = createResultCard(colName, colData);
        container.appendChild(card);
    }
}
```

**Streamlit:**
```python
for col_name, col_data in results.items():
    with st.container():
        st.markdown(f"### {col_name}")
        
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"**Value:** {col_data['value']}")
        with col2:
            st.markdown(f"**Page:** {col_data['page_number']}")
        with col3:
            st.markdown(f"**Modality:** {col_data['modality']}")
```

### Comparison View

**Flask:**
```html
<!-- comparison.html -->
<div id="sidebar">
    <h2>Column Groups</h2>
    <div id="sidebar-groups"></div>
</div>

<script src="static/js/comparison.js"></script>
```

**Streamlit:**
```python
with st.sidebar:
    st.markdown("### Column Groups")
    
    for group_name in groups:
        if st.button(f"{group_name} ({len(columns)})"):
            st.session_state.selected_group = group_name
            st.rerun()
```

## 🚀 Migration Steps

### Step 1: Install Streamlit

```bash
pip install streamlit pandas
```

### Step 2: Test Basic Functionality

```bash
# Run Streamlit app alongside Flask
streamlit run web/streamlit_app.py
```

### Step 3: Compare Features

Use both interfaces side-by-side to verify feature parity.

### Step 4: Gradual Migration

**Option A: Parallel Operation**
- Keep both running
- Gradually move users to Streamlit
- Deprecate Flask when ready

**Option B: Full Switch**
- Test thoroughly in development
- Switch in one deployment
- Keep Flask as backup

### Step 5: Cleanup (Optional)

After successful migration:
```bash
# Backup Flask code
mkdir -p backups
tar -czf backups/flask_interface_$(date +%Y%m%d).tar.gz \
    web/templates web/static web/main_app.py

# Remove Flask files (optional)
# rm -rf web/templates web/static
# rm web/main_app.py
```

## 📝 Code Changes Required

### Minimal Changes Needed

The good news: **No changes to backend services required!**

Both Flask and Streamlit use the same:
- `extraction_service.py`
- `comparison_service.py`
- `highlight_service.py`
- `explainability_service.py`

### Custom Features Migration

If you have custom Flask features, here's how to migrate:

**1. Custom API Endpoints**
```python
# Flask
@app.route('/api/custom', methods=['POST'])
def custom_endpoint():
    data = request.get_json()
    result = process_data(data)
    return jsonify(result)

# Streamlit
with st.form("custom_form"):
    data = st.text_input("Input")
    if st.form_submit_button("Submit"):
        result = process_data(data)
        st.json(result)
```

**2. Custom Visualizations**
```python
# Flask: Use Chart.js or D3.js in HTML

# Streamlit: Use built-in or Plotly
import plotly.express as px
fig = px.bar(data, x='column', y='value')
st.plotly_chart(fig)
```

**3. Authentication**
```python
# Flask: Use Flask-Login

# Streamlit: Use streamlit-authenticator
import streamlit_authenticator as stauth
authenticator = stauth.Authenticate(...)
name, authentication_status, username = authenticator.login()
```

## 🎯 Best Practices

### When to Use Flask

✅ Need full control over UI/UX
✅ Complex custom visualizations
✅ Integration with existing Flask apps
✅ Advanced authentication/authorization
✅ Custom JavaScript interactions

### When to Use Streamlit

✅ Rapid prototyping
✅ Internal tools and dashboards
✅ Data exploration interfaces
✅ Easy deployment
✅ Python-only team
✅ Minimal UI customization needed

## 🔧 Configuration

### Flask Configuration

```python
# config.py
class Config:
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024
    UPLOAD_FOLDER = 'uploads'
    DEBUG = False

app.config.from_object(Config)
```

### Streamlit Configuration

```toml
# .streamlit/config.toml
[server]
maxUploadSize = 50

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
```

## 📦 Deployment

### Flask Deployment

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 web.main_app:app

# Using uWSGI
uwsgi --http :5000 --wsgi-file web/main_app.py --callable app
```

### Streamlit Deployment

```bash
# Local
streamlit run web/streamlit_app.py

# Cloud (Streamlit Cloud)
# Just push to GitHub and connect

# Docker
FROM python:3.9
COPY . /app
WORKDIR /app
RUN pip install -r web/streamlit_requirements.txt
EXPOSE 8501
CMD ["streamlit", "run", "web/streamlit_app.py"]
```

## 🐛 Common Migration Issues

### Issue 1: Session State

**Flask:** Uses server-side sessions or cookies
**Streamlit:** Uses `st.session_state`

**Solution:**
```python
# Initialize in Streamlit
if 'key' not in st.session_state:
    st.session_state.key = value
```

### Issue 2: File Uploads

**Flask:** `request.files`
**Streamlit:** `st.file_uploader()`

**Solution:** Both save to same location, no backend changes.

### Issue 3: Async Operations

**Flask:** Can use async routes
**Streamlit:** Synchronous by default

**Solution:** Use `st.spinner()` for long operations or threading.

### Issue 4: Custom Styling

**Flask:** Full CSS control
**Streamlit:** Limited CSS injection

**Solution:**
```python
st.markdown("""
<style>
.custom-class { /* your styles */ }
</style>
""", unsafe_allow_html=True)
```

## 📊 Performance Comparison

| Metric | Flask | Streamlit |
|--------|-------|-----------|
| Initial Load | Fast | Medium |
| Interactions | Fast | Medium-Fast |
| Large Data | Fast | Medium |
| Concurrent Users | High | Medium |
| Memory Usage | Low | Medium |

**Note:** Streamlit re-runs script on interaction, which can be slower for very large datasets.

## 🎓 Learning Resources

### Streamlit
- [Official Docs](https://docs.streamlit.io)
- [Gallery](https://streamlit.io/gallery)
- [Cheat Sheet](https://docs.streamlit.io/library/cheatsheet)

### Flask to Streamlit
- [Why Streamlit](https://streamlit.io/why-streamlit)
- [Best Practices](https://docs.streamlit.io/library/advanced-features)

## ✅ Decision Checklist

Use this checklist to decide which interface to use:

**Choose Streamlit if:**
- [ ] You want rapid development
- [ ] Team is primarily Python developers
- [ ] UI customization is not critical
- [ ] Building internal tools/dashboards
- [ ] Need quick prototyping

**Keep Flask if:**
- [ ] You need full UI control
- [ ] Have existing Flask infrastructure
- [ ] Need complex custom JavaScript
- [ ] Require specific authentication
- [ ] Need maximum performance

**Use Both if:**
- [ ] Different use cases (internal vs external)
- [ ] Gradual migration strategy
- [ ] A/B testing interfaces
- [ ] Different user groups

## 📞 Support

For migration questions:
1. Check this guide
2. Review code examples in both interfaces
3. Test in development environment
4. Consult Streamlit documentation

## 🎉 Conclusion

Both interfaces are fully functional and use the same backend. Choose based on your needs:

- **Flask**: Maximum control and flexibility
- **Streamlit**: Ease of use and rapid development

The Streamlit interface provides all the same features with significantly less code and easier maintenance.
