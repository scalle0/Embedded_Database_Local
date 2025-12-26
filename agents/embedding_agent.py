"""Embedding agent - handles text chunking and vector embedding generation."""

import time
from typing import Dict, Any, List, Optional
from pathlib import Path
import hashlib
from functools import lru_cache
from collections import OrderedDict

from .base_agent import BaseAgent, DocumentData


class LRUCache:
    """LRU Cache with maximum size limit to prevent memory overflow."""

    def __init__(self, max_size: int = 10000):
        """Initialize LRU cache.

        Args:
            max_size: Maximum number of items to cache
        """
        self.cache = OrderedDict()
        self.max_size = max_size

    def get(self, key: str) -> Optional[Any]:
        """Get item from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if key in self.cache:
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            return self.cache[key]
        return None

    def put(self, key: str, value: Any):
        """Put item in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        if key in self.cache:
            # Update existing item
            self.cache.move_to_end(key)
        else:
            # Add new item
            self.cache[key] = value

            # Evict oldest if over limit
            if len(self.cache) > self.max_size:
                self.cache.popitem(last=False)

    def __len__(self):
        return len(self.cache)

    def clear(self):
        """Clear all cached items."""
        self.cache.clear()


class EmbeddingAgent(BaseAgent):
    """Agent for chunking text and generating embeddings using Gemini API."""

    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize embedding agent.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        self.chunking_config = config.get('chunking', {})
        self.gemini_config = config.get('gemini', {})

        # Initialize text splitter
        self._init_text_splitter()

        # Initialize Gemini embeddings
        self._init_gemini_embeddings()

        # Embedding cache to avoid reprocessing
        # Use LRU cache with max size to prevent memory overflow
        cache_size = config.get('embedding', {}).get('cache_size', 10000)
        self.embedding_cache = LRUCache(max_size=cache_size)
        self.cache_hits = 0
        self.cache_misses = 0

    def _init_text_splitter(self):
        """Initialize text chunking/splitting strategy."""
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
            import tiktoken

            self.tiktoken = tiktoken

            # Get chunking parameters
            chunk_size = self.chunking_config.get('chunk_size', 800)
            chunk_overlap = self.chunking_config.get('chunk_overlap', 200)

            # Create splitter
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                length_function=self._count_tokens,
                separators=["\n\n", "\n", ". ", " ", ""],
                keep_separator=True
            )

            self.logger.info(
                f"Text splitter initialized: chunk_size={chunk_size}, "
                f"overlap={chunk_overlap}"
            )

        except ImportError:
            self.logger.warning(
                "langchain-text-splitters not available, using simple chunking"
            )
            self.text_splitter = None
            self.tiktoken = None

    def _init_gemini_embeddings(self):
        """Initialize Gemini embeddings API."""
        try:
            from google import genai

            api_key = self.gemini_config.get('api_key')

            if not api_key or api_key.startswith('${'):
                raise ValueError("Gemini API key not configured")

            # Initialize client with new SDK
            self.genai_client = genai.Client(api_key=api_key)

            # Get embedding model
            self.embedding_model_name = self.gemini_config.get(
                'embedding_model',
                'models/text-embedding-004'
            )

            self.logger.info(f"Gemini embeddings initialized: {self.embedding_model_name}")

        except ImportError:
            raise RuntimeError(
                "google-genai not available. "
                "Install with: pip install google-genai"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize Gemini embeddings: {e}")

    def _count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count

        Returns:
            Number of tokens
        """
        if self.tiktoken:
            try:
                encoding = self.tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                pass

        # Fallback: rough estimate (1 token ≈ 4 characters)
        return len(text) // 4

    def process(self, doc: DocumentData) -> DocumentData:
        """Chunk text and generate embeddings.

        Args:
            doc: DocumentData with extracted text in content field

        Returns:
            DocumentData with chunks and embeddings
        """
        if not doc.content:
            self.log_skip(f"{doc.file_path.name}: No content to embed")
            return doc

        if doc.processing_status == 'failed':
            self.log_skip(f"{doc.file_path.name}: Previous processing failed")
            return doc

        try:
            # Chunk the text
            chunks = self._chunk_text(doc.content, doc.metadata)

            if not chunks:
                self.log_error(f"No chunks created for {doc.file_path.name}")
                doc.errors.append("Chunking failed")
                return doc

            doc.chunks = chunks

            # Generate embeddings (with batching for efficiency)
            embeddings = self._generate_embeddings([chunk['text'] for chunk in chunks])

            if embeddings:
                # Attach embeddings to chunks
                for chunk, embedding in zip(chunks, embeddings):
                    chunk['embedding'] = embedding

                doc.embeddings = embeddings
                doc.processing_status = 'completed'

                self.log_success(
                    f"Embedded {doc.file_path.name}: "
                    f"{len(chunks)} chunks, {len(embeddings)} embeddings"
                )
            else:
                self.log_error(f"Failed to generate embeddings for {doc.file_path.name}")
                doc.errors.append("Embedding generation failed")

        except Exception as e:
            self.log_error(f"Embedding failed for {doc.file_path.name}", e)
            doc.processing_status = 'failed'
            doc.errors.append(f"Embedding error: {str(e)}")

        return doc

    def _chunk_text(
        self,
        text: str,
        metadata: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Split text into chunks.

        Args:
            text: Text to chunk
            metadata: Document metadata to attach to each chunk

        Returns:
            List of chunk dictionaries
        """
        if self.text_splitter:
            # Use LangChain splitter
            text_chunks = self.text_splitter.split_text(text)
        else:
            # Simple fallback chunking
            chunk_size = self.chunking_config.get('chunk_size', 800)
            text_chunks = self._simple_chunk(text, chunk_size)

        # Create chunk objects with metadata
        chunks = []
        for idx, chunk_text in enumerate(text_chunks):
            # Skip very small chunks
            if len(chunk_text.strip()) < self.chunking_config.get('min_chunk_size', 100):
                continue

            chunk = {
                'text': chunk_text,
                'chunk_index': idx,
                'char_count': len(chunk_text),
                'token_count': self._count_tokens(chunk_text),
                'metadata': metadata.copy()
            }

            # Add chunk-specific metadata
            chunk['metadata']['chunk_index'] = idx

            chunks.append(chunk)

        return chunks

    def _simple_chunk(self, text: str, chunk_size: int) -> List[str]:
        """Simple text chunking fallback.

        Args:
            text: Text to chunk
            chunk_size: Target chunk size in tokens

        Returns:
            List of text chunks
        """
        # Approximate characters per chunk (1 token ≈ 4 chars)
        char_chunk_size = chunk_size * 4
        overlap = self.chunking_config.get('chunk_overlap', 200) * 4

        chunks = []
        start = 0

        while start < len(text):
            end = start + char_chunk_size

            # Try to break at paragraph
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind('\n\n', start, end)
                if para_break > start:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    sent_break = text.rfind('. ', start, end)
                    if sent_break > start:
                        end = sent_break + 2

            chunks.append(text[start:end])
            start = end - overlap if end < len(text) else end

        return chunks

    def _generate_embeddings(
        self,
        texts: List[str],
        batch_size: int = 100
    ) -> List[List[float]]:
        """Generate embeddings for text chunks using Gemini API.

        Args:
            texts: List of text chunks
            batch_size: Number of texts to embed in one API call

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]

            # Check cache first
            batch_embeddings = []
            uncached_texts = []
            uncached_indices = []

            for j, text in enumerate(batch):
                text_hash = self._hash_text(text)

                cached_embedding = self.embedding_cache.get(text_hash)
                if cached_embedding is not None:
                    batch_embeddings.append(cached_embedding)
                    self.cache_hits += 1
                else:
                    uncached_texts.append(text)
                    uncached_indices.append(j)
                    batch_embeddings.append(None)  # Placeholder
                    self.cache_misses += 1

            # Generate embeddings for uncached texts
            if uncached_texts:
                # Retry with exponential backoff
                max_retries = self.gemini_config.get('max_retries', 3)
                retry_delay = 1.0

                for retry in range(max_retries):
                    try:
                        # Call Gemini API with new SDK
                        response = self.genai_client.models.embed_content(
                            model=self.embedding_model_name,
                            contents=uncached_texts
                        )

                        # Extract embeddings from new API response
                        new_embeddings = [embedding.values for embedding in response.embeddings]

                        # Cache and insert embeddings
                        for text, embedding, idx in zip(uncached_texts, new_embeddings, uncached_indices):
                            text_hash = self._hash_text(text)
                            self.embedding_cache.put(text_hash, embedding)
                            batch_embeddings[idx] = embedding

                        self.logger.debug(
                            f"Generated {len(new_embeddings)} embeddings "
                            f"(cache hits: {self.cache_hits}, misses: {self.cache_misses})"
                        )

                        # Rate limiting
                        time.sleep(0.1)  # 10 requests per second max
                        break  # Success, exit retry loop

                    except Exception as e:
                        error_msg = str(e).lower()

                        # Check if it's a rate limit error
                        if 'rate limit' in error_msg or 'quota' in error_msg or '429' in error_msg:
                            if retry < max_retries - 1:
                                self.logger.warning(
                                    f"Rate limit hit, retrying in {retry_delay}s "
                                    f"(attempt {retry + 1}/{max_retries})"
                                )
                                time.sleep(retry_delay)
                                retry_delay *= 2  # Exponential backoff
                                continue
                            else:
                                self.logger.error(f"Rate limit exceeded after {max_retries} retries")
                                return all_embeddings
                        else:
                            # Non-rate-limit error
                            self.logger.error(f"Gemini API error: {e}")
                            if retry < max_retries - 1:
                                self.logger.info(f"Retrying... (attempt {retry + 1}/{max_retries})")
                                time.sleep(retry_delay)
                                retry_delay *= 2
                                continue
                            else:
                                # Return partial results after all retries
                                return all_embeddings

            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    def _hash_text(self, text: str) -> str:
        """Generate hash for text caching.

        Args:
            text: Text to hash

        Returns:
            Hash string
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()

    def batch_process(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Process multiple documents in batch.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed DocumentData objects
        """
        processed = []

        for doc in documents:
            processed_doc = self.process(doc)
            processed.append(processed_doc)

        return processed

    def save_cache(self, cache_file: Optional[Path] = None):
        """Save embedding cache to disk.

        Args:
            cache_file: Path to cache file
        """
        if cache_file is None:
            cache_file = Path(self.config.get('directories', {}).get('processed', '.')) / 'embedding_cache.pkl'

        try:
            import pickle
            cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Convert LRU cache to dict for pickling
            cache_dict = dict(self.embedding_cache.cache)

            with open(cache_file, 'wb') as f:
                pickle.dump(cache_dict, f)

            self.logger.info(f"Saved {len(self.embedding_cache)} cached embeddings to {cache_file}")

        except Exception as e:
            self.logger.error(f"Failed to save cache: {e}")

    def load_cache(self, cache_file: Optional[Path] = None):
        """Load embedding cache from disk.

        Args:
            cache_file: Path to cache file
        """
        if cache_file is None:
            cache_file = Path(self.config.get('directories', {}).get('processed', '.')) / 'embedding_cache.pkl'

        if not cache_file.exists():
            self.logger.info("No cache file found")
            return

        try:
            import pickle

            with open(cache_file, 'rb') as f:
                cache_dict = pickle.load(f)

            # Load into LRU cache (will auto-trim if over max_size)
            if isinstance(cache_dict, dict):
                for key, value in cache_dict.items():
                    self.embedding_cache.put(key, value)
                self.logger.info(f"Loaded {len(self.embedding_cache)} cached embeddings from {cache_file}")
            else:
                self.logger.warning("Cache file format not recognized, starting with empty cache")

        except Exception as e:
            self.logger.error(f"Failed to load cache: {e}")
