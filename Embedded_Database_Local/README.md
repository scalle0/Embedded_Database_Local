# Multi-Agent Document Processing & Embedding System

A comprehensive document processing pipeline that ingests various file formats, extracts text using OCR and parsers, generates embeddings via Google Gemini, and stores them in a ChromaDB vector database for semantic search.

## Features

### 📄 Supported File Formats
- **Documents**: PDF, DOCX, DOC, TXT, Markdown
- **Emails**: EML, MSG
- **Notes**: Evernote ENEX files
- **Images**: PNG, JPG, JPEG, TIFF, BMP

### 🤖 Multi-Agent Architecture

1. **Ingestion Agent** - Discovers and validates files, handles duplicates
2. **OCR Agent** - Hybrid approach with Tesseract, EasyOCR, and Gemini fallback
3. **Extraction Agent** - Extracts text from PDFs, DOCX, emails, ENEX
4. **Embedding Agent** - Smart chunking and Gemini embeddings generation
5. **Database Agent** - ChromaDB vector storage and retrieval
6. **Orchestrator** - Coordinates the entire pipeline

### 🔍 OCR Strategy

- **Local First**: Uses Tesseract and EasyOCR for standard typed text
- **Confidence-Based Fallback**: If OCR confidence < 70%, uses Gemini Vision API
- **Optimized for Handwriting**: EasyOCR handles handwritten text, with Gemini as backup

### 💾 Vector Database

- **ChromaDB**: Persistent local vector store
- **Gemini Embeddings**: High-quality embeddings via `text-embedding-004`
- **Metadata Support**: Rich metadata filtering (date, type, tags, etc.)
- **Semantic Search**: Find documents by meaning, not just keywords

### 🎯 Search Interfaces

- **Streamlit Web UI** ⭐: Beautiful web interface with exact quote extraction
- **Interactive CLI**: Terminal-based search interface
- **Programmatic API**: Python API for custom integrations

#### Quote Extraction Features
- Automatically extracts relevant quotes from search results
- Shows context before and after quotes
- Highlights query terms in results
- Configurable context window
- View full documents from results

## Installation

### 1. System Requirements

**Python**: 3.10 or higher

**OCR Dependencies** (optional but recommended):
```bash
# macOS
brew install tesseract
brew install tesseract-lang  # For Dutch + English support

# Ubuntu/Debian
sudo apt-get install tesseract-ocr
sudo apt-get install tesseract-ocr-nld tesseract-ocr-eng

# Windows
# Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
```

### 2. Install Python Dependencies

```bash
cd Embedded_Database_Local

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure API Keys

Create a `.env` file (copy from `.env.example`):

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```
GEMINI_API_KEY=your_gemini_api_key_here
```

**Get a Gemini API key**: https://makersuite.google.com/app/apikey

### 4. Configure Settings (Optional)

Edit `config/config.yaml` to customize:
- OCR settings (languages, confidence thresholds)
- Chunking parameters (size, overlap)
- Processing options (parallel workers, batch size)
- Database location

## Usage

### Process Documents

#### Basic Usage

```bash
# Process all files in configured input directory (data/input/)
python main.py

# Process specific file
python main.py --input /path/to/document.pdf

# Process entire directory
python main.py --input /path/to/documents/
```

#### Advanced Options

```bash
# Use sequential processing (more stable, slower)
python main.py --no-parallel

# Reset database before processing (WARNING: deletes all data)
python main.py --reset-db

# Use custom configuration file
python main.py --config /path/to/custom_config.yaml
```

### Query the Database

#### Streamlit Web Interface (Recommended) ⭐

Launch the beautiful web interface with exact quote extraction:

```bash
streamlit run streamlit_app.py
```

The app opens in your browser at `http://localhost:8501`

**Features**:
- 🔍 Semantic search with natural language
- 📌 **Automatic quote extraction** with context
- 📄 Full document viewer
- 🎯 Advanced filtering (file type, date, similarity)
- 💡 Highlighted search terms
- 📊 Real-time database statistics

See [STREAMLIT_GUIDE.md](STREAMLIT_GUIDE.md) for detailed usage.

#### Interactive CLI

```bash
python query_interface.py
```

This launches a terminal-based interface where you can:
- Search by semantic meaning
- View results with similarity scores
- See full document text
- Filter by metadata

#### Example Search Session

```
Document Search Interface
================================================================================

Database contains:
  - 1250 chunks
  - 45 unique source documents

--------------------------------------------------------------------------------
Enter search query (or 'quit' to exit): medical records from 2023

Number of results (default 10): 5

Found 5 results:

[1] Score: 0.892
    Source: patient_records.pdf
    Type: pdf
    Text: Medical examination report dated January 15, 2023...

[2] Score: 0.854
    Source: Diana_medical_2023.enex
    Type: enex
    Text: Follow-up appointment notes from March 2023...
```

### Programmatic Usage

```python
from query_interface import QueryInterface

# Initialize
qi = QueryInterface()

# Semantic search
results = qi.search("handwritten medical notes", n_results=10)

# Metadata-only search
results = qi.search_by_metadata(
    filters={'file_type': 'pdf', 'tags': 'medical'},
    n_results=20
)

# Get all chunks from a specific document
chunks = qi.get_document_chunks('path/to/document.pdf')

# Database statistics
stats = qi.get_statistics()
print(f"Total chunks: {stats['total_chunks']}")
```

## Project Structure

```
Embedded_Database_Local/
├── agents/                     # Processing agents
│   ├── base_agent.py          # Base agent class
│   ├── ingestion_agent.py     # File discovery & validation
│   ├── ocr_agent.py           # OCR with hybrid approach
│   ├── extraction_agent.py    # Text extraction (PDF/DOCX/email/ENEX)
│   ├── embedding_agent.py     # Chunking & embedding generation
│   ├── database_agent.py      # ChromaDB management
│   └── orchestrator.py        # Pipeline coordinator
│
├── utils/                      # Utilities
│   ├── config_loader.py       # Configuration management
│   └── logger.py              # Logging setup
│
├── config/                     # Configuration
│   └── config.yaml            # Main configuration file
│
├── data/                       # Data directories
│   ├── input/                 # Put files here for processing
│   ├── processed/             # Successfully processed files
│   ├── failed/                # Failed processing files
│   ├── chromadb/              # Vector database storage
│   └── logs/                  # Log files
│
├── main.py                     # Main entry point
├── query_interface.py          # Search interface
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
└── README.md                  # This file
```

## Workflow

### 1. Prepare Your Documents

Place all documents in the `data/input/` directory:

```bash
cp /path/to/documents/* data/input/
```

Supported formats: `.pdf`, `.docx`, `.enex`, `.eml`, `.msg`, `.png`, `.jpg`, etc.

### 2. Run Processing Pipeline

```bash
python main.py
```

The pipeline will:
1. **Ingest**: Discover files, check for duplicates
2. **Extract/OCR**: Extract text (with OCR for images/scanned PDFs)
3. **Embed**: Chunk text and generate embeddings
4. **Store**: Save to ChromaDB with metadata
5. **Report**: Show processing statistics

### 3. Search Your Documents

```bash
python query_interface.py
```

Search using natural language queries!

## Configuration Guide

### OCR Settings

```yaml
ocr:
  tesseract:
    enabled: true
    language: "nld+eng"          # Dutch + English
    confidence_threshold: 70      # Use Gemini if below this

  easyocr:
    enabled: true
    languages: ["nl", "en"]
    gpu: false                    # Set true if you have CUDA GPU

  gemini_fallback:
    enabled: true
    use_when_confidence_below: 70  # Confidence threshold
```

### Chunking Strategy

```yaml
chunking:
  chunk_size: 800                 # Tokens per chunk
  chunk_overlap: 200              # Overlap between chunks
  respect_boundaries: true        # Don't split paragraphs
  min_chunk_size: 100            # Skip chunks smaller than this
```

### Processing Options

```yaml
pipeline:
  batch_size: 10                  # Documents in parallel
  max_workers: 4                  # Thread pool size
  skip_duplicates: true           # Skip already-processed files
  continue_on_error: true         # Keep going if some files fail
```

## Advanced Features

### Duplicate Detection

The system automatically detects and skips duplicate files using SHA256 hashing. Processed hashes are saved to `data/processed/.hashes`.

### Embedding Cache

Generated embeddings are cached to avoid re-processing identical text chunks. Cache is saved to `data/processed/embedding_cache.pkl`.

### Metadata Filtering

Search with metadata filters:

```python
results = qi.search(
    "medical records",
    filters={
        'file_type': 'pdf',
        'created_date': '2023-01-01'
    }
)
```

### Custom Prompts

Customize the Gemini OCR prompt in `config/config.yaml`:

```yaml
ocr:
  gemini_fallback:
    prompt: "Extract all text including handwritten notes. Preserve structure."
```

## Troubleshooting

### "Gemini API key not configured"

Make sure you've set `GEMINI_API_KEY` in your `.env` file:

```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

### "pytesseract not available"

Install Tesseract OCR system package:

```bash
# macOS
brew install tesseract

# Ubuntu
sudo apt-get install tesseract-ocr
```

Then install Python wrapper:

```bash
pip install pytesseract
```

### "chromadb not available"

Install ChromaDB:

```bash
pip install chromadb
```

### Low OCR Accuracy

1. Check image quality (increase DPI if scanning)
2. Enable image preprocessing in `config.yaml`
3. Lower the Gemini fallback threshold to use AI more often
4. For handwriting, ensure EasyOCR is installed and enabled

### Rate Limiting (Gemini API)

The system includes automatic rate limiting (10 requests/second). If you hit limits:

1. Reduce `batch_size` in config
2. Add `time.sleep()` in `embedding_agent.py` after API calls
3. Consider upgrading your Gemini API quota

## Performance Tips

### 1. Use GPU for EasyOCR

If you have a CUDA-compatible GPU:

```yaml
ocr:
  easyocr:
    gpu: true
```

### 2. Parallel Processing

For large batches, use parallel processing (default):

```bash
python main.py  # Parallel enabled
```

For stability with limited resources:

```bash
python main.py --no-parallel
```

### 3. Optimize Chunk Size

Smaller chunks = more embeddings = slower but more precise
Larger chunks = fewer embeddings = faster but less precise

Recommended: 600-1000 tokens

### 4. Cache Everything

The system caches:
- Embeddings (avoid re-generating)
- Processed file hashes (skip duplicates)

Don't delete cache files unless you want to reprocess!

## API Costs (Gemini)

### Embeddings
- Model: `text-embedding-004`
- Cost: Free tier available, then ~$0.00001 per 1K tokens
- 1000 chunks ≈ $0.01

### OCR (Vision)
- Model: `gemini-2.0-flash-exp`
- Only used for low-confidence OCR (handwriting)
- Cost: Free tier available, then ~$0.001 per image

**Estimate**: Processing 1000 mixed documents costs ~$0.10-$0.50 depending on OCR usage.

## Integration with Existing Scripts

Your existing ENEX processing scripts can feed into this system:

```bash
# 1. Convert ENEX to Markdown (existing scripts)
python ../enex_to_markdown

# 2. Move Markdown files to input directory
mv ../All_Notes_Markdown/*.md data/input/

# 3. Process and embed
python main.py
```

## Future Enhancements

Potential improvements:

- [ ] Web interface (Gradio/Streamlit)
- [ ] Support for more formats (RTF, ODT, HTML)
- [ ] Re-ranking with cross-encoder
- [ ] Hybrid search (vector + BM25)
- [ ] Automatic tagging with LLM
- [ ] PDF table extraction
- [ ] Multi-lingual support expansion
- [ ] Export to other vector DBs (Pinecone, Weaviate)

## License

MIT License - feel free to use and modify!

## Support

For issues or questions:
1. Check configuration in `config/config.yaml`
2. Review logs in `data/logs/pipeline.log`
3. Enable DEBUG logging in config for detailed output

---

Built with ❤️ using Claude Code
