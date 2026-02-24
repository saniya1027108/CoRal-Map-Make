# Streamlit Interface Guide

A visual guide to navigating and using the Clinical Trial Data Extraction Streamlit interface.

## 🏠 Home Page - Extract Data

### Page Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar                │  Main Content Area                │
│  ─────────              │  ──────────────────               │
│  🧭 Navigation          │                                   │
│  ├─ 🏠 Home             │  🏥 Clinical Trial Data          │
│  └─ 📊 Compare          │     Extraction                    │
│                         │                                   │
│  📋 About               │  AI-powered extraction of...      │
│  Features:              │                                   │
│  • Single column        │  ┌─────────────────────────────┐ │
│  • All columns          │  │ 📄 Step 1: Upload PDF      │ │
│  • Custom CSV           │  │                             │ │
│  • Comparison           │  │  [Drag & Drop PDF]          │ │
│  • PDF highlighting     │  │  or                         │ │
│                         │  │  [Browse Files Button]      │ │
│                         │  └─────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Steps

#### Step 1: Upload PDF
```
┌────────────────────────────────────────┐
│  📄 Upload PDF Document                │
├────────────────────────────────────────┤
│                                        │
│     [Drag & Drop Area]                 │
│                                        │
│     Maximum file size: 50MB            │
│                                        │
│     [Browse Files]                     │
│                                        │
└────────────────────────────────────────┘
                 ↓ (upload success)
┌────────────────────────────────────────┐
│  ✓ PDF Loaded Successfully             │
│  File: document.pdf (2.5 MB)           │
└────────────────────────────────────────┘
```

#### Step 2: Select Method
```
┌─────────────────────────────────────────────────────────────┐
│  🎯 Step 2: Select Extraction Method                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │  🎯 Extract  │  │  📋 Extract  │  │  📊 Custom   │    │
│  │     Value    │  │   All Data   │  │     CSV      │    │
│  │              │  │              │  │              │    │
│  │  Extract for │  │  View 133    │  │  Upload CSV  │    │
│  │  specific    │  │  columns     │  │  with custom │    │
│  │  column      │  │              │  │  queries     │    │
│  │              │  │              │  │              │    │
│  │  [Select]    │  │  [Select]    │  │  [Select]    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

#### Method A: Extract Single Value
```
┌────────────────────────────────────────┐
│  🎯 Extract Value          [← Back]    │
├────────────────────────────────────────┤
│                                        │
│  Select Column                         │
│  [Dropdown: -- Select --           ▼] │
│    - NCT                               │
│    - Treatment Arm 1 Regimen           │
│    - Primary Endpoint                  │
│    - ...                               │
│                                        │
│  Or Enter Custom Column                │
│  [Text input: e.g., Trial Name    ]   │
│                                        │
│  Custom Definition (optional)          │
│  [Text area:                      ]   │
│  [                                 ]   │
│                                        │
│  [    Extract Value    ]               │
└────────────────────────────────────────┘
```

#### Method B: Extract All Data
```
┌────────────────────────────────────────┐
│  📋 Extract All Data       [← Back]    │
├────────────────────────────────────────┤
│                                        │
│  ℹ️ View Existing Extractions          │
│  Select a document to view complete    │
│  133-column extraction data            │
│                                        │
│  Select Document                       │
│  [Dropdown:                        ▼] │
│    - NCT00309985 (gemini-2.0-flash)   │
│    - NCT01234567 (gemini-2.0-flash)   │
│    - ...                               │
│                                        │
│  [  Load Extraction Data  ]            │
└────────────────────────────────────────┘
```

#### Method C: Custom CSV
```
┌────────────────────────────────────────┐
│  📊 Custom CSV Extraction  [← Back]    │
├────────────────────────────────────────┤
│                                        │
│  ℹ️ CSV Format Requirements:           │
│  • Must contain: column_name,          │
│    definition                          │
│  • Example: NCT,"What is..."           │
│                                        │
│  [Choose CSV File] selected.csv        │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │ CSV Preview                      │ │
│  │ column_name  | definition        │ │
│  │ NCT          | What is...        │ │
│  │ Trial Name   | Name of...        │ │
│  └──────────────────────────────────┘ │
│                                        │
│  [  Extract from CSV  ]                │
└────────────────────────────────────────┘
```

#### Step 3: View Results
```
┌─────────────────────────────────────────────────────────────┐
│  📊 Extraction Results                                      │
├─────────────────────────────────────────────────────────────┤
│  Total: 5 columns    [Export JSON] [Export CSV] [View: ▼] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Card View:                                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ NCT                                                   │ │
│  │ Value: NCT00309985    Page: 1      Modality: text    │ │
│  │ [🔍 View Evidence ▼]                                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Primary Endpoint                                      │ │
│  │ Value: Overall Survival  Page: 3   Modality: text    │ │
│  │ [🔍 View Evidence ▼]                                  │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  Table View:                                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Column Name  │ Value    │ Page │ Modality │ Evidence │ │
│  ├──────────────┼──────────┼──────┼──────────┼──────────┤ │
│  │ NCT          │ NCT00... │ 1    │ text     │ Found... │ │
│  │ Primary...   │ Overall..│ 3    │ text     │ From...  │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 📊 Compare Extraction Results Page

### Document List View

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Compare Extraction Results                              │
├─────────────────────────────────────────────────────────────┤
│  Browse documents and compare results across Gemini,        │
│  Landing AI, and pipeline methods.                          │
│                                                             │
│  🔍 Search: [Search documents...                        ]  │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ NCT00309985  │ │ NCT01234567  │ │ NCT02345678  │      │
│  │              │ │              │ │              │      │
│  │ Methods:     │ │ Methods:     │ │ Methods:     │      │
│  │ 🟣 Gemini    │ │ 🟣 Gemini    │ │ 🟡 Landing AI│      │
│  │ 🟡 Landing AI│ │ 🔵 Pipeline  │ │ 🔵 Pipeline  │      │
│  │              │ │              │ │              │      │
│  │ [View →]     │ │ [View →]     │ │ [View →]     │      │
│  └──────────────┘ └──────────────┘ └──────────────┘      │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐      │
│  │ ...          │ │ ...          │ │ ...          │      │
│  └──────────────┘ └──────────────┘ └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

### Document Detail View

```
┌─────────────────────────────────────────────────────────────┐
│  [← Back]  📄 NCT00309985                                   │
│            Methods: Gemini, Landing AI, Pipeline            │
├─────────────────────────────────────────────────────────────┤
│  📈 Extraction Summary                                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐          │
│  │ Gemini     │  │ Landing AI │  │ Pipeline   │          │
│  │ 98/133     │  │ 95/133     │  │ 102/133    │          │
│  │ ▼ 35 empty │  │ ▼ 38 empty │  │ ▼ 31 empty │          │
│  └────────────┘  └────────────┘  └────────────┘          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┬─────────────────────────┬───────────────┐│
│  │ Sidebar     │ Main Content            │ PDF Viewer    ││
│  │             │                         │               ││
│  │ 📑 Groups   │ [Group Snapshot         │ 📄 Source     ││
│  │             │  or Column Detail]      │               ││
│  │ 📁 Study    │                         │ Page: 3       ││
│  │    Design   │ ┌─────────────────────┐ │               ││
│  │    (15)     │ │ Primary Endpoint    │ │ [PDF with    ││
│  │             │ │                     │ │  highlights] ││
│  │ 📁 Baseline │ │ 🟣 Gemini:          │ │               ││
│  │    (20)     │ │ Value: Overall...   │ │               ││
│  │             │ │ Page: 3             │ │               ││
│  │ 📁 Results  │ │ Evidence: Found in..│ │               ││
│  │    (30)     │ │                     │ │               ││
│  │             │ │ 🟡 Landing AI:      │ │               ││
│  │ 📁 Adverse  │ │ Value: Overall...   │ │ [Download]   ││
│  │    Events   │ │ Page: 3             │ │               ││
│  │    (25)     │ │ Evidence: Extracted.│ │               ││
│  │             │ └─────────────────────┘ │               ││
│  └─────────────┴─────────────────────────┴───────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### Group Snapshot View

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Study Design (15 columns)                               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Column          │ Gemini        │ Landing AI    │ Pipeline│
│  ───────────────────────────────────────────────────────────│
│  NCT             │ NCT00309985   │ NCT00309985   │ NCT00.. │
│                  │               │               │ [Detail]│
│  Trial Name      │ CHAARTED      │ CHAARTED      │ CHAAR.. │
│                  │               │               │ [Detail]│
│  Primary Endpt   │ Overall Sur.. │ Overall Sur.. │ Overa.. │
│                  │               │               │ [Detail]│
│  ...             │ ...           │ ...           │ ...     │
│                                                             │
│  [Show All 15 Columns]                                      │
└─────────────────────────────────────────────────────────────┘
```

### Column Detail View

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Primary Endpoint                          [← Back]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🟣 Gemini ▼                                                │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Value: Overall Survival    Page: 3    Source: text   │ │
│  │                                                       │ │
│  │ Evidence:                                             │ │
│  │ The primary endpoint was overall survival from the    │ │
│  │ time of randomization. Secondary endpoints included...│ │
│  │                                                       │ │
│  │ Confidence: 🟢 high                                   │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  🟡 Landing AI ▼                                            │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Value: Overall Survival    Page: 3    Source: text   │ │
│  │                                                       │ │
│  │ Evidence:                                             │ │
│  │ Primary outcome measure: Overall survival from date...│ │
│  │                                                       │ │
│  │ Confidence: 🟡 medium                                 │ │
│  └───────────────────────────────────────────────────────┘ │
│                                                             │
│  🔵 Pipeline ▼                                              │
│  ┌───────────────────────────────────────────────────────┐ │
│  │ Value: Overall Survival    Page: 3    Source: table  │ │
│  │                                                       │ │
│  │ Evidence:                                             │ │
│  │ Extracted from Table 1: Study Characteristics...      │ │
│  │                                                       │ │
│  │ Confidence: 🟢 high                                   │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## 🎯 Common Tasks

### Task 1: Extract Single Column from New PDF
```
1. Upload PDF (Step 1)
2. Click "🎯 Extract Value"
3. Select column from dropdown
4. Click "Extract Value"
5. View results with evidence
6. Export if needed
```

### Task 2: View All Columns from Existing Extraction
```
1. Upload any PDF (to activate interface)
2. Click "📋 Extract All Data"
3. Select document from dropdown
4. Click "Load Extraction Data"
5. Toggle between Card/Table view
6. Export if needed
```

### Task 3: Compare Methods for a Document
```
1. Navigate to "📊 Compare Extraction Results"
2. Click "View Details" on document
3. Check summary cards at top
4. Select a group from sidebar
5. View comparison table
6. Click "Details" on any column
```

### Task 4: Find Evidence in PDF
```
1. In Comparison view, select document
2. Select a column group
3. Click on specific column
4. View evidence from each method
5. Check PDF viewer on right
6. Highlights show source location
```

### Task 5: Export Results
```
1. After extraction, scroll to results
2. Click "Export JSON" or "Export CSV"
3. File downloads automatically
4. Open in Excel or text editor
```

## 🔄 Navigation Flow

```
Home Page (Extract)
  ↓
Upload PDF
  ↓
Choose Method ──→ Extract Value ──→ Results
              │
              ├─→ Extract All ───→ Results
              │
              └─→ Custom CSV ───→ Results
                                   ↓
                              Export Data


Comparison Page
  ↓
Document List
  ↓
Select Document
  ↓
View Summary Cards
  ↓
Select Group ──→ Group Snapshot ──→ Column Detail
                                      ↓
                                 PDF Evidence
```

## 💡 Tips & Tricks

### Interface Tips
- 🔍 **Search**: Use search box to quickly find documents
- 📊 **Views**: Toggle between card and table views for different perspectives
- 📁 **Groups**: Use groups to organize columns by category
- 🔽 **Expand**: Click arrows to expand/collapse sections
- 📥 **Export**: Always export before starting new extraction

### Performance Tips
- ⚡ **PDF Size**: Keep under 50MB for faster uploads
- 🎯 **Single Column**: Faster than extracting all columns
- 📋 **Pre-computed**: Use "Extract All Data" for instant results
- 🔄 **Refresh**: If interface is slow, refresh browser

### Workflow Tips
- 🎯 **Start Simple**: Try single column first
- 📊 **Compare**: Use comparison view to verify results
- 📝 **CSV Batch**: Use CSV for multiple custom columns
- 💾 **Save Results**: Export important results immediately

## ⌨️ Keyboard Shortcuts

Streamlit supports standard browser shortcuts:
- **Ctrl/Cmd + R**: Refresh page
- **Ctrl/Cmd + F**: Find on page
- **Ctrl/Cmd + S**: Save (when focused on download button)
- **Tab**: Navigate between inputs
- **Enter**: Submit forms

## 📱 Mobile Usage

The interface is fully responsive on mobile devices:

```
Mobile View (Portrait)
┌──────────────────┐
│ ☰ Menu          │
│ Clinical Trial   │
│ Data Extraction  │
├──────────────────┤
│                  │
│ [Upload PDF]     │
│                  │
│ [Methods]        │
│                  │
│ [Results]        │
│                  │
│ (Scrollable)     │
│                  │
└──────────────────┘
```

Mobile Tips:
- Use hamburger menu (☰) for navigation
- All features work, just stacked vertically
- Pinch to zoom on PDF viewer
- Landscape mode for better table viewing

## 🎨 Color Coding

### Method Colors
- 🟣 **Gemini**: Purple/Violet
- 🟡 **Landing AI**: Yellow/Amber
- 🔵 **Pipeline**: Blue/Cyan

### Status Colors
- 🟢 **High Confidence**: Green
- 🟡 **Medium Confidence**: Yellow
- 🔴 **Low Confidence**: Red
- ⚪ **Unknown**: White/Gray

### UI Elements
- 🔵 **Primary Actions**: Blue buttons
- ⚪ **Secondary Actions**: Gray buttons
- 🟢 **Success**: Green messages
- 🔴 **Error**: Red messages
- 🟡 **Warning**: Yellow messages
- 🔵 **Info**: Blue messages

## ❓ Quick Reference

### File Requirements
- **PDF**: .pdf extension, max 50MB
- **CSV**: column_name and definition columns required

### API Key
- **Required for**: New extractions
- **Not required for**: Viewing existing results
- **Set with**: `export GEMINI_API_KEY="your-key"`

### Browser Support
- ✅ Chrome (recommended)
- ✅ Firefox
- ✅ Safari
- ✅ Edge
- ⚠️ IE (not supported)

## 🆘 Quick Help

### Something not working?
1. Check browser console (F12) for errors
2. Refresh the page (Ctrl/Cmd + R)
3. Clear session state (restart app)
4. Check QUICKSTART.md for setup

### Need more help?
- 📖 Read STREAMLIT_README.md (full documentation)
- 🚀 Check QUICKSTART.md (quick setup)
- 🔄 See MIGRATION_GUIDE.md (technical details)
- ✅ Run test_streamlit.py (verify setup)

---

**Happy Extracting!** 🎉
