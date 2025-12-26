# Troubleshooting Guide

Common issues and their solutions.

## Installation Issues

### "pip install failed for chromadb"

**Error**: Build errors when installing ChromaDB

**Solution**:
```bash
# Update pip and setuptools
pip install --upgrade pip setuptools wheel

# Install chromadb
pip install chromadb
```

If still failing on macOS:
```bash
# Install build dependencies
brew install cmake

# Try again
pip install chromadb
```

### "pytesseract not available"

**Error**: `pytesseract not available` during OCR

**Solution**:

1. Install Tesseract system package:
```bash
# macOS
brew install tesseract tesseract-lang

# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-nld tesseract-ocr-eng

# Windows
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
```

2. Install Python wrapper:
```bash
pip install pytesseract
```

3. Verify installation:
```bash
tesseract --version
```

### "EasyOCR failed to initialize"

**Error**: EasyOCR installation or initialization fails

**Solution**:

```bash
# Install with specific version
pip install easyocr==1.7.1

# If you have a CUDA GPU
pip install torch torchvision

# For CPU only
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

Disable EasyOCR in config if not needed:
```yaml
ocr:
  easyocr:
    enabled: false
```

## Configuration Issues

### "Gemini API key not configured"

**Error**: `ValueError: Gemini API key not configured`

**Solution**:

1. Get API key from: https://makersuite.google.com/app/apikey

2. Create `.env` file:
```bash
echo "GEMINI_API_KEY=your_key_here" > .env
```

3. Verify it's loaded:
```python
import os
from dotenv import load_dotenv

load_dotenv()
print(os.getenv('GEMINI_API_KEY'))  # Should print your key
```

### "Config file not found"

**Error**: `FileNotFoundError: Config file not found`

**Solution**:

Ensure `config/config.yaml` exists:
```bash
ls -la config/config.yaml
```

If missing, the file should be in the repository. Check you're in the right directory:
```bash
pwd  # Should end with Embedded_Database_Local
```

### "Invalid configuration value"

**Error**: YAML parsing errors

**Solution**:

Check YAML syntax:
```bash
python -c "import yaml; yaml.safe_load(open('config/config.yaml'))"
```

Common issues:
- Indentation (use spaces, not tabs)
- Missing colons
- Unquoted special characters

## Runtime Errors

### "No documents found to process"

**Error**: Pipeline reports 0 documents

**Possible Causes**:

1. **Empty input directory**:
```bash
ls -la data/input/  # Should show files
```

Solution: Copy files to input directory:
```bash
cp /path/to/documents/* data/input/
```

2. **Unsupported file formats**:
Check `config.yaml`:
```yaml
pipeline:
  supported_formats:
    - .pdf
    - .docx
    # Add your format here
```

3. **All files already processed** (duplicates):
```bash
cat data/processed/.hashes  # Check if files are already processed
```

Solution: Delete hash file to reprocess:
```bash
rm data/processed/.hashes
```

### "Gemini API rate limit exceeded"

**Error**: `429 Too Many Requests` from Gemini API

**Solution**:

1. **Reduce batch size** in `config.yaml`:
```yaml
pipeline:
  batch_size: 5  # Reduce from 10
```

2. **Add delay** in `agents/embedding_agent.py`:
```python
# In _generate_embeddings method, increase sleep:
time.sleep(0.2)  # Increase from 0.1
```

3. **Use caching**: Enable embedding cache to reduce API calls

4. **Upgrade API quota**: Check Google AI Studio for limits

### "ChromaDB collection error"

**Error**: Issues with ChromaDB collection

**Solution**:

1. **Reset database**:
```bash
python main.py --reset-db
```

2. **Delete ChromaDB directory**:
```bash
rm -rf data/chromadb/
python main.py  # Will recreate
```

3. **Check permissions**:
```bash
ls -la data/chromadb/
chmod -R 755 data/chromadb/
```

### "Out of memory"

**Error**: System runs out of RAM

**Solutions**:

1. **Disable parallel processing**:
```bash
python main.py --no-parallel
```

2. **Reduce workers** in `config.yaml`:
```yaml
pipeline:
  max_workers: 2  # Reduce from 4
```

3. **Process in smaller batches**:
```bash
# Process one file at a time
for file in data/input/*; do
    python main.py --input "$file"
done
```

4. **Reduce chunk size**:
```yaml
chunking:
  chunk_size: 500  # Reduce from 800
```

## OCR Issues

### "OCR produces gibberish"

**Issue**: OCR output is nonsensical

**Solutions**:

1. **Check image quality**: Ensure DPI ≥ 300
2. **Enable preprocessing**: Verify OpenCV is installed
3. **Try Gemini fallback**: Lower confidence threshold

```yaml
ocr:
  gemini_fallback:
    use_when_confidence_below: 90  # Increase from 70
```

### "Low OCR confidence"

**Issue**: Confidence scores consistently < 50%

**Solutions**:

1. **Improve image quality**:
   - Scan at higher DPI (300-600)
   - Use denoising/sharpening
   - Ensure good contrast

2. **Enable all OCR engines**:
```yaml
ocr:
  tesseract:
    enabled: true
  easyocr:
    enabled: true
```

3. **Use Gemini for all images**:
```yaml
ocr:
  gemini_fallback:
    use_when_confidence_below: 100  # Always use Gemini
```

### "Handwriting not recognized"

**Issue**: Handwritten text not extracted

**Solution**:

Handwriting is difficult. Best approach:

1. **Enable EasyOCR** (better than Tesseract for handwriting)
2. **Use Gemini fallback** (best for handwriting):
```yaml
ocr:
  gemini_fallback:
    enabled: true
    use_when_confidence_below: 80
    prompt: "Extract all text including handwritten notes. For unclear text, use [unclear]."
```

## Search/Query Issues

### "Query returns no results"

**Issue**: Searches return 0 results

**Debugging**:

1. **Check database has data**:
```python
from query_interface import QueryInterface
qi = QueryInterface()
stats = qi.get_statistics()
print(stats)  # Should show chunks > 0
```

2. **Try broader query**:
```python
# Instead of specific query
results = qi.search("medical records from Dr. Smith on January 15th")

# Try broader
results = qi.search("medical")
```

3. **Lower similarity threshold**:
```python
results = qi.search("query", min_similarity=0.5)  # Lower from 0.7
```

4. **Check metadata filters**:
```python
# Remove filters to test
results = qi.search("query", filters=None)
```

### "Query results not relevant"

**Issue**: Results don't match query intent

**Solutions**:

1. **Rephrase query**: Try different wording
2. **Increase results**: Get more candidates
```python
results = qi.search("query", n_results=50)
```

3. **Check chunking**: Chunks might be too small/large
```yaml
chunking:
  chunk_size: 1000  # Increase for more context
```

4. **Use metadata filters**: Narrow by type/date
```python
results = qi.search("query", filters={'file_type': 'pdf'})
```

## Performance Issues

### "Processing is very slow"

**Solutions**:

1. **Enable parallel processing** (default):
```bash
python main.py  # Already parallel
```

2. **Increase workers**:
```yaml
pipeline:
  max_workers: 8  # Increase if you have CPU cores
```

3. **Use GPU for EasyOCR**:
```yaml
ocr:
  easyocr:
    gpu: true  # Requires CUDA
```

4. **Profile bottlenecks**:
Check logs to see which stage is slow:
```bash
grep "Processing\|Extraction\|Embedding" data/logs/pipeline.log
```

### "Embedding generation slow"

**Issue**: Embedding step takes forever

**Solutions**:

1. **Use embedding cache**: Should be automatic, verify:
```bash
ls -la data/processed/embedding_cache.pkl
```

2. **Batch processing**: Already enabled, but verify config:
```yaml
pipeline:
  batch_size: 100  # Higher = faster but more memory
```

3. **Check API latency**: Gemini API might be slow
   - Monitor API response times in logs
   - Try different regions (VPN)

### "Database queries slow"

**Issue**: Searches take > 5 seconds

**Solutions**:

1. **Reduce n_results**:
```python
results = qi.search("query", n_results=10)  # Not 100
```

2. **Add metadata filters** (makes queries faster):
```python
results = qi.search("query", filters={'file_type': 'pdf'})
```

3. **Rebuild index**:
```bash
python main.py --reset-db
python main.py  # Reprocess everything
```

## Debugging Tips

### Enable Debug Logging

Edit `config/config.yaml`:
```yaml
logging:
  level: "DEBUG"  # Change from INFO
```

Check logs:
```bash
tail -f data/logs/pipeline.log
```

### Inspect Document Processing

Add debug statements in code:
```python
# In main.py or agents
import json

# After processing a document
print(json.dumps(doc.to_dict(), indent=2))
```

### Test Single Document

Process one file to isolate issues:
```bash
python main.py --input data/input/test.pdf
```

### Interactive Python Session

```python
from utils.config_loader import get_config
from agents.orchestrator import Orchestrator

config = get_config()
orch = Orchestrator(config.get_all())

# Test individual agents
doc = orch.ingestion_agent.process()
print(doc[0].to_dict())

# Test OCR
doc_with_ocr = orch.ocr_agent.process(doc[0])
print(doc_with_ocr.content[:500])
```

### Check API Keys

```python
import os
from dotenv import load_dotenv

load_dotenv()
print(f"Gemini: {os.getenv('GEMINI_API_KEY')[:10]}...")  # First 10 chars
```

## Common Error Messages

### "No module named 'chromadb'"
**Solution**: `pip install chromadb`

### "No module named 'google.generativeai'"
**Solution**: `pip install google-generativeai`

### "No module named 'dotenv'"
**Solution**: `pip install python-dotenv`

### "No module named 'fitz'"
**Solution**: `pip install PyMuPDF`

### "ModuleNotFoundError: No module named 'cv2'"
**Solution**: `pip install opencv-python`

### "CUDA not available"
**Not an error**: Just means no GPU acceleration. System will use CPU (slower but works).

To enable GPU (optional):
```bash
# If you have NVIDIA GPU with CUDA
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

## Getting Help

### Check Logs First

```bash
# View recent errors
grep ERROR data/logs/pipeline.log | tail -20

# View processing stats
grep "Processing complete" data/logs/pipeline.log
```

### Validate Configuration

```bash
python -c "from utils.config_loader import get_config; c = get_config(); c.validate(); print('Config OK')"
```

### Run Tests

```bash
# Test database connection
python -c "from agents.database_agent import DatabaseAgent; from utils.config_loader import get_config; db = DatabaseAgent(get_config().get_all()); print(db.get_stats())"

# Test Gemini API
python -c "import google.generativeai as genai; import os; from dotenv import load_dotenv; load_dotenv(); genai.configure(api_key=os.getenv('GEMINI_API_KEY')); print('Gemini OK')"
```

### Clean Start

If all else fails, start fresh:

```bash
# Backup your data
cp -r data/input data/input_backup

# Clean everything
rm -rf data/chromadb data/processed data/failed data/logs
rm -rf venv

# Reinstall
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Restore data
mv data/input_backup/* data/input/

# Reprocess
python main.py
```

## Still Having Issues?

Create an issue with:

1. **Error message** (full traceback)
2. **Configuration** (sanitized config.yaml)
3. **System info**:
```bash
python --version
pip list | grep -E "chromadb|google-generativeai|pytesseract"
uname -a
```

4. **Steps to reproduce**
5. **Relevant logs** from `data/logs/pipeline.log`
