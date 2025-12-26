# Quick Start Guide

Get your document search system running in 5 minutes!

## Step 1: Install Dependencies

```bash
cd Embedded_Database_Local
bash setup.sh
```

Or manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create directories
mkdir -p data/{input,processed,failed,chromadb,logs}
```

## Step 2: Configure API Keys

Get your API keys:
- **Gemini** (required): https://makersuite.google.com/app/apikey
- **Anthropic** (optional, for best OCR): https://console.anthropic.com/

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your keys
cat > .env << EOF
GEMINI_API_KEY=your_gemini_key_here
ANTHROPIC_API_KEY=your_anthropic_key_here  # Optional but recommended for handwriting
EOF
```

**Note**: Claude (Anthropic) provides the best OCR for handwritten documents. Gemini is used as fallback.

## Step 3: Add Documents

```bash
# Copy your documents to the input folder
cp /path/to/your/documents/* data/input/
```

Supported formats: PDF, DOCX, ENEX, images, emails, etc.

## Step 4: Process Documents

```bash
python main.py
```

This will:
- Extract text from all documents
- Use OCR on images and scanned PDFs
- Generate embeddings
- Store in ChromaDB

## Step 5: Search!

### Option 1: Web Interface (Recommended) ⭐

```bash
streamlit run streamlit_app.py
```

Opens in your browser with:
- 📌 Automatic quote extraction
- 📄 Full document viewer
- 🎯 Visual filters and settings
- 💡 Highlighted results

### Option 2: Terminal Interface

```bash
python query_interface.py
```

Enter your search queries in natural language!

## Example Workflow

```bash
# 1. Setup
bash setup.sh

# 2. Add your Gemini API key to .env
nano .env

# 3. Copy documents
cp ~/Documents/*.pdf data/input/

# 4. Process everything
python main.py

# 5. Search
python query_interface.py
```

Then search for things like:
- "medical records from 2023"
- "handwritten notes about Diana"
- "correspondence with Dr. Smith"

## Tips

**First time processing?** Start with a few documents to test:
```bash
python main.py --input data/input/test_document.pdf
```

**Re-processing?** The system automatically skips duplicates.

**Errors?** Check `data/logs/pipeline.log` for details.

**Reset database?**
```bash
python main.py --reset-db
```

That's it! You now have a powerful semantic search system for all your documents.

For more details, see [README.md](README.md)
