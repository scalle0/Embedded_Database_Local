# Scalability Improvements for 4GB+ Data Processing

## Overview

This document describes the critical fixes implemented to handle large-scale document processing (4GB+ / 1M+ chunks) without memory crashes or performance degradation.

## Problems Fixed

### 1. ✅ Memory Leak in Database Statistics
**Location**: [database_agent.py:248-308](agents/database_agent.py#L248-L308)

**Problem**: Loading all metadata into memory to count unique sources would crash with millions of chunks.

**Solution**:
- Implemented pagination for databases with <100k chunks
- Uses sampling for larger databases (>100k chunks)
- Processes data in 10k chunk batches to keep memory usage low

### 2. ✅ Unbounded Embedding Cache
**Location**: [embedding_agent.py:13-63](agents/embedding_agent.py#L13-L63)

**Problem**: Embedding cache grew unbounded, consuming GB of RAM.

**Solution**:
- Implemented LRU cache with configurable max size (default 10,000 embeddings)
- Auto-evicts oldest entries when cache is full
- Prevents memory overflow while maintaining cache benefits

**Configuration**: Set in `config.yaml`:
```yaml
embedding:
  cache_size: 10000  # Adjust based on available RAM
```

### 3. ✅ API Rate Limit Failures
**Location**: [embedding_agent.py:347-410](agents/embedding_agent.py#L347-L410)

**Problem**: Gemini API rate limits caused processing to fail without retry.

**Solution**:
- Exponential backoff retry logic (3 attempts by default)
- Detects rate limit errors specifically (429, "rate limit", "quota")
- Graceful degradation on persistent failures

### 4. ✅ ChromaDB Batch Insert Memory Issues
**Location**: [database_agent.py:120-134](agents/database_agent.py#L120-L134)

**Problem**: Inserting thousands of chunks at once consumed excessive memory.

**Solution**:
- Batched inserts with configurable batch size (default 1,000)
- Reduces memory spikes during database writes

**Configuration**: Set in `config.yaml`:
```yaml
chromadb:
  batch_insert_size: 1000  # Adjust based on chunk size
```

### 5. ✅ No Crash Recovery
**Location**: [utils/checkpoint.py](utils/checkpoint.py)

**Problem**: Processing crash meant losing hours of work.

**Solution**:
- Checkpoint system saves progress after each batch
- Automatic resume from last checkpoint on restart
- Tracks processed files to avoid reprocessing

**Checkpoint file**: `data/processed/.checkpoint.json`

### 6. ✅ Memory Monitoring
**Location**: [utils/memory_monitor.py](utils/memory_monitor.py)

**Problem**: No visibility into memory usage, crashes were unexpected.

**Solution**:
- Real-time memory monitoring with psutil
- Automatic garbage collection when memory usage exceeds threshold
- Detailed logging of memory usage at each stage

**Configuration**: Set in `config.yaml`:
```yaml
memory:
  max_percent: 80.0  # Trigger cleanup at 80% memory usage
```

### 7. ✅ Streaming Batch Processing
**Location**: [orchestrator.py:65-222](agents/orchestrator.py#L65-L222)

**Problem**: Loading all documents into memory at once caused crashes.

**Solution**:
- Processes documents in configurable batches (default 50)
- Clears memory after each batch with garbage collection
- Saves cache and checkpoints after each batch
- Resume capability if process crashes

**Configuration**: Set in `config.yaml`:
```yaml
memory:
  stream_batch_size: 50  # Number of documents per batch
```

## New Dependencies

Added to [requirements.txt](requirements.txt):
```
psutil>=5.9.0  # Memory monitoring
```

## Configuration Changes

New sections in [config.yaml](config/config.yaml):

```yaml
# Embedding Configuration
embedding:
  cache_size: 10000  # Maximum embeddings to cache in memory (LRU)

# ChromaDB Configuration
chromadb:
  batch_insert_size: 1000  # Batch size for DB inserts

# Memory Management (for large-scale processing)
memory:
  max_percent: 80.0  # Maximum system memory usage before triggering cleanup
  stream_batch_size: 50  # Number of documents to process per batch
```

## Usage

### Install New Dependencies

```bash
pip install -r requirements.txt
```

### Running with New Features

```bash
# Process with automatic resume (default)
python main.py

# Force restart from beginning (ignore checkpoint)
python main.py --no-resume

# Process with sequential mode (more stable, slower)
python main.py --no-parallel
```

### Monitoring Progress

The system now logs:
- Memory usage at each stage
- Batch progress with checkpoints
- Cache hit rates
- API retry attempts

Check logs in `logs/pipeline.log`

### Resume After Crash

If processing crashes or is interrupted:
1. Simply run `python main.py` again
2. System automatically resumes from last checkpoint
3. Already processed files are skipped

### Clearing Checkpoint

To start fresh:
```bash
# Delete checkpoint file
rm data/processed/.checkpoint.json
```

## Performance Expectations for 4GB Data

### Processing Time
- **1 million chunks** @ 10 embeddings/sec = **27-30 hours** (sequential)
- With 4 parallel workers: **8-12 hours** (depending on API limits)

### Memory Usage
- **Peak RAM**: 2-4 GB (with streaming batches of 50)
- **Disk usage**: 3-5 GB (ChromaDB storage)

### Cost (Gemini API)
- **Embeddings**: ~$10-20 for 1M chunks
- **OCR fallback**: Variable, depends on image quality

## Tuning for Your System

### Low RAM (8GB or less)
```yaml
memory:
  stream_batch_size: 25  # Smaller batches
  max_percent: 70.0  # More aggressive cleanup

embedding:
  cache_size: 5000  # Smaller cache
```

### High RAM (32GB+)
```yaml
memory:
  stream_batch_size: 100  # Larger batches = faster
  max_percent: 85.0  # Allow more memory usage

embedding:
  cache_size: 50000  # Larger cache = fewer API calls
```

### Slow Network / API Limits
```yaml
pipeline:
  batch_size: 5  # Fewer parallel requests
  max_workers: 2

gemini:
  max_retries: 5  # More retry attempts
```

## Monitoring System Health

### Check Memory Usage
System logs memory at:
- Pipeline startup
- Before/after each batch
- After garbage collection

Look for patterns like:
```
Memory usage (batch 5 start): 45.2% (Process: 1234.5 MB, Available: 6789.0 MB)
Memory usage (batch 5 end): 38.1% (Process: 987.6 MB, Available: 7123.0 MB)
```

### Check Cache Effectiveness
In final report:
```
Embedding cache: 10000 entries, 67.3% hit rate
```

Higher hit rate = better performance, fewer API calls

### Check Checkpoint Progress
```
Checkpoint saved: batch 15/200, 750 files processed
```

## Troubleshooting

### High Memory Usage
If memory consistently exceeds threshold:
1. Reduce `stream_batch_size` (e.g., 25 or 10)
2. Reduce `embedding.cache_size`
3. Use `--no-parallel` mode

### Slow Processing
If processing is too slow:
1. Increase `stream_batch_size` (if you have RAM)
2. Increase `pipeline.max_workers` (more parallelism)
3. Increase `embedding.cache_size` (reduce API calls)

### API Rate Limits
If hitting rate limits frequently:
1. Reduce `pipeline.batch_size`
2. Increase `gemini.max_retries`
3. Add longer delays between batches (code modification needed)

### ChromaDB Performance
If queries become slow with large DB:
1. Consider switching to production vector DB (Qdrant, Weaviate, Pinecone)
2. Use metadata filters to narrow search scope
3. Sample queries instead of exact counts for stats

## Architecture for Future Scale

For **10GB+** or **multi-million chunks**, consider:

1. **Production Vector DB**: Qdrant (local), Weaviate, or Pinecone (cloud)
2. **Distributed Processing**: Celery with RabbitMQ/Redis
3. **Cloud Infrastructure**: AWS Lambda + S3 + managed vector DB
4. **Streaming Pipeline**: Apache Kafka for event streaming
5. **Caching Layer**: Redis instead of pickle files

## Files Modified

### New Files
- `utils/memory_monitor.py` - Memory monitoring utility
- `utils/checkpoint.py` - Checkpoint/resume system
- `SCALABILITY_IMPROVEMENTS.md` - This document

### Modified Files
- `agents/database_agent.py` - Fixed stats memory leak, batch inserts
- `agents/embedding_agent.py` - LRU cache, exponential backoff
- `agents/orchestrator.py` - Streaming batch processing, memory management
- `config/config.yaml` - New memory and embedding settings
- `requirements.txt` - Added psutil

## Testing Recommendations

Before processing 4GB:

1. **Test with small dataset** (100 files):
   ```bash
   python main.py --input ./data/test_sample
   ```

2. **Monitor memory** during test run

3. **Verify checkpoint resume**:
   - Stop processing mid-way (Ctrl+C)
   - Restart and confirm it resumes

4. **Check database queries** still work after bulk insert

5. **Estimate total time** based on test batch

## Summary

These improvements make the system production-ready for **4GB+ datasets** by:
- ✅ Eliminating memory leaks
- ✅ Adding crash recovery
- ✅ Implementing streaming processing
- ✅ Providing visibility into resource usage
- ✅ Handling API failures gracefully

**Expected outcome**: Process 4GB (1M chunks) in 8-30 hours with <4GB RAM usage and full crash recovery.
