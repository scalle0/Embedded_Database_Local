# System Architecture

## Overview

The system follows a **multi-agent pipeline architecture** where specialized agents handle different aspects of document processing. The Orchestrator coordinates all agents and manages the workflow.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                          USER INPUT                                     │
│                    (Files/Directories)                                  │
│                              │                                          │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                      ORCHESTRATOR AGENT                                 │
│                                                                         │
│  • Coordinates all agents                                              │
│  • Manages processing pipeline                                         │
│  • Handles errors and retries                                          │
│  • Tracks statistics                                                   │
│  • Parallel/sequential execution                                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
                ▼              ▼              ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│                     │  │                     │  │                     │
│  INGESTION AGENT    │  │  EXTRACTION AGENT   │  │    OCR AGENT        │
│                     │  │                     │  │                     │
│  • File discovery   │  │  • PDF text layer   │  │  • Tesseract OCR    │
│  • Type detection   │  │  • DOCX parsing     │  │  • EasyOCR          │
│  • Duplicate check  │  │  • Email parsing    │  │  • Image preproc.   │
│  • Hash generation  │  │  • ENEX parsing     │  │  • Confidence calc. │
│  • Metadata extract │  │  • Plain text       │  │  • Gemini fallback  │
│                     │  │                     │  │                     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
                               │                              │
                               └──────────┬───────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │                                 │
                         │      EMBEDDING AGENT            │
                         │                                 │
                         │  • Smart text chunking          │
                         │  • Token counting               │
                         │  • Paragraph respect            │
                         │  • Gemini embeddings API        │
                         │  • Embedding cache              │
                         │  • Batch processing             │
                         │                                 │
                         └─────────────────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │                                 │
                         │      DATABASE AGENT             │
                         │                                 │
                         │  • ChromaDB management          │
                         │  • Metadata storage             │
                         │  • Vector indexing              │
                         │  • Query execution              │
                         │  • Similarity search            │
                         │                                 │
                         └─────────────────────────────────┘
                                          │
                                          ▼
                         ┌─────────────────────────────────┐
                         │                                 │
                         │   CHROMADB VECTOR STORE         │
                         │                                 │
                         │  • Persistent storage           │
                         │  • HNSW indexing                │
                         │  • Cosine similarity            │
                         │  • Metadata filtering           │
                         │                                 │
                         └─────────────────────────────────┘
                                          │
                                          │
                         ┌────────────────┴────────────────┐
                         │                                 │
                         │     QUERY INTERFACE             │
                         │                                 │
                         │  • Semantic search              │
                         │  • Metadata filtering           │
                         │  • Result ranking               │
                         │  • Interactive CLI              │
                         │  • Programmatic API             │
                         │                                 │
                         └─────────────────────────────────┘
                                          │
                                          ▼
                                   ┌─────────────┐
                                   │             │
                                   │    USER     │
                                   │   RESULTS   │
                                   │             │
                                   └─────────────┘
```

## Data Flow

### Processing Pipeline

```
Input Document
    │
    ├─→ [1] Ingestion Agent
    │       ├─→ File type detection
    │       ├─→ Duplicate check (SHA256)
    │       ├─→ Metadata extraction (size, date, etc.)
    │       └─→ Create DocumentData object
    │
    ├─→ [2] Extraction/OCR Agent (parallel routing)
    │       │
    │       ├─→ IF image/scanned PDF:
    │       │       └─→ OCR Agent
    │       │           ├─→ Tesseract (typed text)
    │       │           ├─→ EasyOCR (handwriting)
    │       │           └─→ Gemini Vision (if confidence < 70%)
    │       │
    │       └─→ IF document:
    │               └─→ Extraction Agent
    │                   ├─→ PDF: PyMuPDF/pdfplumber
    │                   ├─→ DOCX: python-docx
    │                   ├─→ Email: extract_msg/email.parser
    │                   └─→ ENEX: XML parsing
    │
    ├─→ [3] Embedding Agent
    │       ├─→ Smart chunking (800 tokens, 200 overlap)
    │       ├─→ Token counting (tiktoken)
    │       ├─→ Gemini embeddings API
    │       └─→ Cache embeddings
    │
    ├─→ [4] Database Agent
    │       ├─→ Flatten metadata
    │       ├─→ Generate chunk IDs
    │       └─→ Store in ChromaDB
    │
    └─→ [5] Completion
            ├─→ Save processing state
            ├─→ Update hash registry
            └─→ Generate statistics
```

### Query Pipeline

```
User Query
    │
    ├─→ [1] Query Interface
    │       └─→ Parse query parameters
    │
    ├─→ [2] Embedding Generation
    │       └─→ Gemini API (task_type: "retrieval_query")
    │
    ├─→ [3] Database Query
    │       ├─→ Vector similarity search
    │       ├─→ Apply metadata filters
    │       └─→ Retrieve top K results
    │
    ├─→ [4] Result Processing
    │       ├─→ Calculate similarity scores
    │       ├─→ Filter by threshold
    │       └─→ Rank by relevance
    │
    └─→ [5] Return Results
            └─→ Format with metadata and scores
```

## Agent Details

### 1. Ingestion Agent

**Responsibility**: File discovery and validation

**Input**: File path or directory
**Output**: List of DocumentData objects

**Key Features**:
- Recursive directory scanning
- File type detection (magic numbers + extension)
- SHA256 duplicate detection
- Metadata extraction (size, dates, etc.)
- Hash registry persistence

**Configuration**:
```yaml
pipeline:
  supported_formats: [.pdf, .docx, .enex, ...]
  skip_duplicates: true
```

### 2. OCR Agent

**Responsibility**: Extract text from images

**Input**: DocumentData with image
**Output**: DocumentData with text + confidence

**Hybrid Strategy**:
1. Try Tesseract (fast, typed text)
2. Try EasyOCR (better for handwriting)
3. If confidence < threshold → Gemini Vision API

**Key Features**:
- Image preprocessing (grayscale, denoise, threshold)
- Confidence scoring
- Automatic fallback to higher-quality OCR
- Multi-language support (Dutch + English)

**Configuration**:
```yaml
ocr:
  tesseract:
    language: "nld+eng"
    confidence_threshold: 70
  gemini_fallback:
    enabled: true
    use_when_confidence_below: 70
```

### 3. Extraction Agent

**Responsibility**: Extract text from documents

**Input**: DocumentData with file
**Output**: DocumentData with text + metadata

**Supported Formats**:
- **PDF**: PyMuPDF (primary), pdfplumber (fallback)
- **DOCX**: python-docx (paragraphs, tables, headers/footers)
- **Email**: extract_msg (.msg), email.parser (.eml)
- **ENEX**: XML parsing with ENML→Markdown conversion

**Key Features**:
- Preserve document structure
- Extract rich metadata (author, dates, etc.)
- Handle encoding issues
- Table extraction

### 4. Embedding Agent

**Responsibility**: Chunk text and generate embeddings

**Input**: DocumentData with text
**Output**: DocumentData with chunks + embeddings

**Chunking Strategy**:
- Recursive character splitting
- Respects paragraph boundaries
- Configurable size (800 tokens default)
- Configurable overlap (200 tokens default)
- Token counting via tiktoken

**Embedding**:
- Gemini `text-embedding-004` API
- Task type: "retrieval_document"
- Batch processing (100 texts/batch)
- Rate limiting (10 req/sec)
- MD5-based caching

**Key Features**:
- Smart chunking (doesn't split sentences)
- Embedding cache (avoid reprocessing)
- Batch API calls (efficiency)
- Token optimization

**Configuration**:
```yaml
chunking:
  chunk_size: 800
  chunk_overlap: 200
  respect_boundaries: true
  min_chunk_size: 100
```

### 5. Database Agent

**Responsibility**: Manage ChromaDB vector store

**Input**: DocumentData with embeddings
**Output**: DocumentData with DB IDs

**Operations**:
- Store: Add chunks with embeddings
- Query: Semantic search
- Delete: Remove by source file
- Stats: Database metrics

**Metadata Handling**:
- Flattens nested dictionaries
- Converts lists to comma-separated strings
- Stores chunk-level metadata

**Key Features**:
- Persistent storage (disk-based)
- HNSW vector indexing
- Cosine similarity metric
- Metadata filtering support

**Configuration**:
```yaml
chromadb:
  persist_directory: "./data/chromadb"
  collection_name: "document_embeddings"
  distance_metric: "cosine"
```

### 6. Orchestrator

**Responsibility**: Coordinate entire pipeline

**Features**:
- Sequential or parallel processing
- Error handling and retry logic
- Progress tracking (tqdm)
- Statistics aggregation
- State persistence

**Workflow**:
1. Ingestion → discover files
2. Extraction/OCR → extract text
3. Embedding → generate vectors
4. Storage → save to DB
5. Cleanup → save state

**Configuration**:
```yaml
pipeline:
  batch_size: 10
  max_workers: 4
  continue_on_error: true
```

## Configuration System

### Hierarchical Configuration

```
config.yaml (base config)
    ↓
Environment Variables (.env)
    ↓
Runtime Parameters (CLI args)
```

### Config Loader

- Loads YAML configuration
- Resolves `${ENV_VAR}` placeholders
- Converts relative paths to absolute
- Validates required keys
- Singleton pattern

## Caching Strategy

### 1. Embedding Cache
- **Location**: `data/processed/embedding_cache.pkl`
- **Key**: MD5 hash of text
- **Value**: Embedding vector
- **Benefits**: Avoid redundant API calls

### 2. File Hash Registry
- **Location**: `data/processed/.hashes`
- **Content**: SHA256 hashes of processed files
- **Benefits**: Skip duplicate files

### 3. ChromaDB Persistence
- **Location**: `data/chromadb/`
- **Format**: SQLite + HNSW index
- **Benefits**: Persistent vector store

## Error Handling

### Graceful Degradation

```
Error in Agent X
    │
    ├─→ Log error with context
    │
    ├─→ Mark document as "failed"
    │
    ├─→ Continue with next document (if continue_on_error=true)
    │
    └─→ Move failed file to data/failed/
```

### Retry Logic

- Configurable max retries
- Exponential backoff for API calls
- Fallback mechanisms (OCR: local → Gemini)

## Performance Optimization

### 1. Parallel Processing
- ThreadPoolExecutor for I/O-bound tasks
- Configurable worker count
- Progress tracking

### 2. Batch Processing
- Gemini API: 100 texts per batch
- Database: Bulk inserts
- Reduces API overhead

### 3. Caching
- Embedding cache (avoid reprocessing)
- File hash registry (skip duplicates)
- In-memory metadata

### 4. Lazy Loading
- Process documents on-demand
- Stream large files
- Chunk-based processing

## Security Considerations

### 1. API Keys
- Stored in `.env` file (not committed)
- Loaded via environment variables
- Never logged or displayed

### 2. File Validation
- File type verification
- Size limits (configurable)
- Malicious file detection

### 3. Sandboxing
- Separate directories (input/processed/failed)
- No file overwrites
- Atomic operations

## Extensibility

### Adding New File Types

1. Update `supported_formats` in config
2. Add extraction logic to `ExtractionAgent`
3. Test with sample files

### Adding New OCR Engines

1. Add initialization in `OCRAgent._init_*`
2. Implement in `_local_ocr()` method
3. Update confidence scoring

### Adding New Vector Databases

1. Create new `DatabaseAgent` subclass
2. Implement: `process()`, `query()`, `delete_by_source()`
3. Update configuration

### Custom Embedding Models

1. Update `EmbeddingAgent._init_*` method
2. Modify `_generate_embeddings()` for new API
3. Update configuration

## Monitoring & Logging

### Log Levels

- **DEBUG**: Detailed processing information
- **INFO**: High-level progress (default)
- **WARNING**: Issues that don't stop processing
- **ERROR**: Processing failures

### Statistics Tracked

Per agent:
- Processed count
- Failed count
- Skipped count

Overall:
- Total chunks in database
- Unique source files
- Cache hit/miss rates
- Processing time (future)

### Log Files

- **Location**: `data/logs/pipeline.log`
- **Rotation**: 10MB max, 5 backups
- **Format**: Timestamp, agent, level, message

## Future Architecture Enhancements

### Planned Features

1. **Web Interface**: Gradio/Streamlit UI
2. **Re-ranking**: Cross-encoder for better results
3. **Hybrid Search**: Vector + BM25 keyword search
4. **Automatic Tagging**: LLM-based categorization
5. **Table Extraction**: Structured data from PDFs
6. **Multi-modal**: Image + text embeddings
7. **Incremental Updates**: Watch folder for new files
8. **Distributed Processing**: Multiple machines

### Scalability Considerations

- Message queue for large batches (Celery/RabbitMQ)
- Distributed vector DB (Pinecone/Weaviate)
- Separate API server for queries
- Kubernetes deployment
