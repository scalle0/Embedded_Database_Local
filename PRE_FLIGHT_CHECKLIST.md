# Pre-Flight Checklist for 4GB Processing

## ✅ Before You Start

### 1. Dependencies
- [ ] Install psutil: `pip install psutil>=5.9.0`
- [ ] Or install all: `pip install -r requirements.txt`
- [ ] Verify installation: `python -c "import psutil; print('OK')"`

### 2. API Keys
- [ ] Copy `.env.example` to `.env`: `cp .env.example .env`
- [ ] Add your Gemini API key to `.env`
- [ ] Add your Anthropic API key to `.env` (optional but recommended for OCR)
- [ ] Verify keys are set: `cat .env` (check both keys are filled in)

### 3. System Requirements
- [ ] Available RAM: At least 8GB (16GB+ recommended)
- [ ] Available disk space: At least 10GB free
- [ ] Check: `df -h .` (disk space) and `vm_stat` (memory on macOS)

### 4. Directory Structure
- [ ] Verify directories exist:
  ```bash
  mkdir -p data/input
  mkdir -p data/processed
  mkdir -p data/failed
  mkdir -p logs
  mkdir -p data/chromadb
  ```
- [ ] Your 4GB files are in `data/input/`
- [ ] Check file count: `ls -lh data/input/ | wc -l`

### 5. Configuration Check
- [ ] Review `config/config.yaml` settings:
  - `memory.stream_batch_size: 50` (adjust if needed)
  - `memory.max_percent: 80.0`
  - `embedding.cache_size: 10000`
  - `chromadb.batch_insert_size: 1000`
- [ ] Log level in `.env` is `LOG_LEVEL=INFO`

### 6. Test Run (HIGHLY RECOMMENDED!)
- [ ] Create test directory: `mkdir -p data/test_sample`
- [ ] Copy 10-20 sample files: `cp data/input/{file1,file2,...} data/test_sample/`
- [ ] Run test: `python main.py --input ./data/test_sample`
- [ ] Verify:
  - No errors in logs
  - Checkpoint file created: `ls data/processed/.checkpoint.json`
  - Memory logs appear: `grep "Memory usage" logs/pipeline.log`
  - Database created: `ls data/chromadb/`

### 7. Git Backup
- [ ] All changes committed to git
- [ ] Pushed to GitHub
- [ ] Can restore if needed: `git log --oneline | head -5`

## 🚀 Ready to Run

### Production Run
```bash
# Start processing 4GB dataset
python main.py

# Monitor progress in another terminal
tail -f logs/pipeline.log
```

### Expected Output
You should see:
```
================================================================================
Starting document processing pipeline (Streaming Mode)
================================================================================

Memory usage (startup): 25.3% (Process: 543.2 MB, Available: 12345.0 MB)

[1/5] Document Ingestion
Discovered 2847 documents

================================================================================
Processing Batch 1/57 (50 documents)
================================================================================

  [2/4] Extracting text from 50 documents
  [3/4] Generating embeddings for 50 documents
  [4/4] Storing 50 documents in database

Checkpoint saved: batch 1/57, 50 files processed
Memory usage (batch 1 end): 32.1% (Process: 987.4 MB, Available: 11234.0 MB)
```

## 📊 Monitoring

### Watch Progress
```bash
# In separate terminal
tail -f logs/pipeline.log
```

### Check Memory
```bash
# Monitor system memory
watch -n 5 'ps aux | grep python | grep main.py'
```

### Check Checkpoint
```bash
# See current progress
cat data/processed/.checkpoint.json
```

## 🛑 If Something Goes Wrong

### Process Crashes
1. Don't panic! Checkpoint saved your progress
2. Check logs: `tail -50 logs/pipeline.log`
3. Just restart: `python main.py`
4. It will resume from last checkpoint

### High Memory Usage
1. Stop the process (Ctrl+C)
2. Reduce batch size in `config/config.yaml`:
   ```yaml
   memory:
     stream_batch_size: 25  # or even 10
   ```
3. Restart: `python main.py`

### API Rate Limits
1. System will auto-retry with exponential backoff
2. Watch logs: `grep "Rate limit" logs/pipeline.log`
3. If persistent, reduce in `config/config.yaml`:
   ```yaml
   pipeline:
     batch_size: 5
     max_workers: 2
   ```

### Database Errors
1. Check disk space: `df -h .`
2. Check ChromaDB directory: `ls -lh data/chromadb/`
3. If corrupted, may need to reset (loses progress):
   ```bash
   python main.py --reset-db
   ```

## ⏱️ Time Estimates

Based on 4GB / ~1M chunks:

- **With defaults (50 docs/batch, 4 workers)**: 8-12 hours
- **Conservative (25 docs/batch, 2 workers)**: 15-20 hours
- **Aggressive (100 docs/batch, 8 workers)**: 6-8 hours (higher memory!)

## 💰 Cost Estimate

- **Gemini embeddings**: $10-$20 for ~1M chunks
- **Claude OCR** (if used): Variable based on images
- **Total estimated**: $15-$30

## ✨ Success Indicators

You'll know it's working when:
- ✅ Memory stays below 80%
- ✅ Batches complete consistently
- ✅ Checkpoints save every batch
- ✅ No persistent errors in logs
- ✅ Database size grows steadily

## 📞 Need Help?

Check the logs first:
```bash
# Last 100 lines
tail -100 logs/pipeline.log

# Search for errors
grep "ERROR" logs/pipeline.log

# Search for warnings
grep "WARNING" logs/pipeline.log
```

---

**When all checkboxes are ticked, you're ready to process 4GB! 🚀**
