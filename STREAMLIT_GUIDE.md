# Streamlit Web Interface Guide

A beautiful, user-friendly web interface for searching your document database with **exact quote extraction** and full document viewing.

---

## 🚀 Quick Start

### Launch the Web Interface

```bash
cd Embedded_Database_Local

# Make sure you've installed dependencies
pip install streamlit

# Launch the web app
streamlit run streamlit_app.py
```

The app will open automatically in your browser at `http://localhost:8501`

---

## ✨ Features

### 1. **Semantic Search with Natural Language**
- Search using plain English queries
- AI-powered similarity matching
- Ranked results by relevance

### 2. **Exact Quote Extraction** ⭐
- Automatically extracts the most relevant sentences
- Shows context before and after quotes
- Highlights multiple quotes per result
- Configurable context window (50-500 characters)

### 3. **Advanced Filtering**
- Filter by file type (PDF, DOCX, images, etc.)
- Filter by date range
- Adjustable similarity threshold
- Limit number of results

### 4. **Full Document Viewer**
- View complete documents from search results
- Search within individual documents
- Browse all chunks with highlighting
- Metadata display (date, OCR confidence, etc.)

### 5. **Beautiful UI**
- Clean, modern interface
- Color-coded similarity scores
- Organized metadata display
- Responsive design

---

## 📖 Using the Interface

### Search Page

#### 1. **Enter Your Query**
Type a natural language question or keywords:

**Examples**:
- "medical examination reports from 2023"
- "handwritten notes about Diana"
- "correspondence with Dr. Smith"
- "documents mentioning medication"

#### 2. **Configure Settings** (Sidebar)

**Search Settings**:
- **Number of results**: 1-50 (default: 10)
- **Minimum similarity**: 0-100% (default: 0%)

**Filters**:
- **File Type**: Filter by PDF, DOCX, images, etc.
- **Date Filter**: Show only documents after a specific date

**Display Options**:
- **Extract quotes**: Toggle quote extraction on/off
- **Context characters**: Adjust context window (50-500)

#### 3. **View Results**

Each result shows:

**Header**:
- 📄 Filename
- 🎯 Similarity score (as percentage)
- 📎 File type badge

**Metadata**:
- 📅 Created date
- 📑 Chunk number
- 🔍 OCR confidence (if applicable)
- 📊 Text length

**Content**:
- **📌 Most Relevant Quote** - Best matching sentence with context
- **Expandable quotes** - See additional quotes from the same chunk
- **Full text** - Complete chunk text in expandable view

**Actions**:
- 📖 **View Full Document** - Open complete document viewer

---

### Quote Display

Quotes are shown with visual highlighting:

```
[context before...] **EXACT QUOTE TEXT** [context after...]
```

- Gray italic text = context
- Bold text = extracted quote
- Green left border = quote box

**Benefits**:
- Get exact quotes you can reference
- Understand context around quotes
- See multiple relevant quotes per chunk
- Copy exact text for citations

---

### Document Viewer

Click "📖 View Full Document" to see:

**Document Header**:
- Filename
- File type
- Creation date
- Total chunks

**Features**:
1. **Search within document** - Find specific terms
2. **Full text view** - Complete reconstructed document
3. **Chunk browser** - View individual chunks separately
4. **Highlighted search terms** - Terms shown in bold

**Navigation**:
- "← Back to Search" - Return to search results

---

## 🎯 Use Cases

### Research & Citations

**Problem**: Need exact quotes with citations

**Solution**:
1. Search for topic: "climate change impacts"
2. View extracted quotes with context
3. Click "View Full Document" to verify
4. Copy exact quote and source filename

### Medical Records Search

**Problem**: Find specific diagnoses across years of records

**Solution**:
1. Search: "diagnosis diabetes"
2. Filter by file type: PDF
3. Set minimum similarity: 70%
4. Review quotes with dates

### Legal Document Review

**Problem**: Find specific clauses in contracts

**Solution**:
1. Search: "termination clause 30 days notice"
2. Extract quotes automatically
3. View full document to read surrounding text
4. Export quotes for review

### Email Archive Search

**Problem**: Find correspondence about specific topics

**Solution**:
1. Filter file type: "eml"
2. Search: "project deadline extension"
3. View quotes with sender/date context
4. Navigate to full email threads

---

## 🔧 Advanced Features

### Quote Relevance Scoring

Quotes are ranked by:
- Keyword overlap with your query
- Position in text
- Sentence completeness

The **best quote** is automatically shown first, with additional quotes in the expandable section.

### Context Window Adjustment

**Small context (50-100 chars)**:
- Focused on exact quote
- Less surrounding text
- Good for short, precise quotes

**Large context (300-500 chars)**:
- More surrounding information
- Better understanding of context
- Good for complex topics

### Similarity Threshold

**0%**: Show all results (default)
- Good for broad exploration
- See all potential matches

**50-70%**: Medium quality
- Balance between quantity and quality
- Filter out very weak matches

**70-100%**: High quality only
- Very relevant results only
- Fewer but better matches

---

## 💡 Tips & Best Practices

### 1. **Start Broad, Then Narrow**
```
Step 1: Search "medical records" → 50 results
Step 2: Add filter (file_type: pdf) → 30 results
Step 3: Increase similarity to 70% → 10 high-quality results
```

### 2. **Use Natural Language**
❌ Bad: "doc pdf 2023 medical"
✅ Good: "medical examination from 2023"

### 3. **Leverage Quote Extraction**
- Enable quotes for research and citations
- Disable for quick browsing of full chunks
- Adjust context based on your needs

### 4. **Multi-Step Research**
```
1. First search: broad topic
2. Note filenames with good results
3. Use "View Full Document" for deep dive
4. Search within document for specifics
```

### 5. **Verify OCR Results**
- Check OCR confidence score in metadata
- Low confidence (<70%)? Review full text carefully
- Handwritten notes may need manual verification

---

## 🎨 Interface Customization

### Changing Theme

Streamlit supports light/dark themes:

1. Click ⋮ (menu) in top right
2. Settings → Theme
3. Choose Light/Dark/Custom

### Sidebar Collapse

- Click `>` to collapse sidebar
- Gives more space for results
- Click `<` to expand again

---

## ⌨️ Keyboard Shortcuts

- `Ctrl/Cmd + K` - Focus search box
- `↑` `↓` - Navigate results
- `Ctrl/Cmd + F` - Search within document
- `Escape` - Clear focus

---

## 📊 Database Statistics

The sidebar shows real-time stats:

- **Total Chunks**: Number of text chunks indexed
- **Unique Documents**: Number of source files

Use these to:
- Monitor database growth
- Verify documents are processed
- Estimate search scope

---

## 🔍 Search Examples

### Example 1: Medical Records

**Query**: "blood test results cholesterol"

**Settings**:
- Results: 10
- Min similarity: 60%
- File type: PDF
- Extract quotes: Yes

**Result**: Get exact quotes mentioning cholesterol with test dates and values

---

### Example 2: Handwritten Notes

**Query**: "handwritten notes meeting"

**Settings**:
- Results: 20
- Min similarity: 0%
- File type: image
- Context: 300 chars

**Result**: View OCR-extracted text from handwritten notes with confidence scores

---

### Example 3: Email Threads

**Query**: "project deadline discussion"

**Settings**:
- File type: eml
- Date filter: After 2023-01-01

**Result**: Email conversations about project deadlines with exact quotes and sender info

---

## 🐛 Troubleshooting

### "Initializing search system..." hangs

**Cause**: Database not initialized

**Solution**:
```bash
# Process some documents first
python main.py --input data/input/sample.pdf

# Then launch Streamlit
streamlit run streamlit_app.py
```

### No results showing

**Causes**:
1. Database is empty
2. Similarity threshold too high
3. Filters too restrictive

**Solutions**:
- Check database stats (sidebar)
- Lower similarity threshold to 0%
- Remove all filters
- Verify documents are processed

### Quotes not extracted

**Cause**: Quote extraction disabled

**Solution**:
- Check "Extract quotes" checkbox in sidebar
- Increase context characters if quotes seem truncated

### Slow performance

**Causes**:
- Large number of results
- Large documents

**Solutions**:
- Reduce number of results (e.g., 10 instead of 50)
- Add filters to narrow search
- Use higher similarity threshold

---

## 🚀 Production Deployment

### Local Network Access

Share with others on your network:

```bash
streamlit run streamlit_app.py --server.address 0.0.0.0
```

Access from other devices: `http://YOUR_IP:8501`

### Cloud Deployment

Deploy to Streamlit Cloud (free):

1. Push code to GitHub
2. Go to https://streamlit.io/cloud
3. Connect your repository
4. Deploy!

**Note**: Set `GEMINI_API_KEY` in Streamlit Cloud secrets.

---

## 📝 Example Session

```
1. Open app: streamlit run streamlit_app.py

2. See database stats:
   - Total chunks: 1,250
   - Unique sources: 45

3. Enter query: "medical examination 2023"

4. Configure:
   - Results: 10
   - Min similarity: 70%
   - File type: PDF
   - Extract quotes: Yes
   - Context: 200 chars

5. Click "Search"

6. Review results:
   Result 1: patient_exam_2023.pdf (Match: 89%)
   Quote: "Annual medical examination completed on March 15, 2023..."
   Context: Full sentence with before/after text

7. Click "View Full Document"

8. Search within: "blood pressure"
   → Highlights all mentions in document

9. Navigate back to continue searching
```

---

## 🎉 Benefits Over CLI

| Feature | CLI | Streamlit |
|---------|-----|-----------|
| **Ease of use** | Terminal commands | Visual interface |
| **Quote extraction** | Manual | Automatic |
| **Document viewing** | File path only | Full viewer |
| **Filtering** | Command flags | Interactive controls |
| **Result browsing** | Text output | Rich formatting |
| **Search history** | None | Session state |
| **Accessibility** | Tech users only | Anyone can use |

---

## 🔗 Next Steps

After mastering the web interface:

1. **Share with team**: Deploy to network/cloud
2. **Automate ingestion**: Watch folder for new docs
3. **Custom views**: Modify `streamlit_app.py` for specific needs
4. **Export results**: Add CSV/PDF export functionality
5. **User authentication**: Add login for sensitive documents

---

## 📞 Need Help?

- Check main documentation: [README.md](README.md)
- Troubleshooting guide: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Architecture details: [ARCHITECTURE.md](ARCHITECTURE.md)

---

**🌟 You now have a powerful, user-friendly search interface with exact quote extraction and full document viewing!**

Enjoy searching your documents! 🔍✨
