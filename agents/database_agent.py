"""Database agent - manages ChromaDB vector store."""

from pathlib import Path
from typing import Dict, Any, List, Optional
import uuid

from .base_agent import BaseAgent, DocumentData


class DatabaseAgent(BaseAgent):
    """Agent for managing ChromaDB vector database."""

    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize database agent.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        self.db_config = config.get('chromadb', {})

        # Initialize ChromaDB
        self._init_chromadb()

    def _init_chromadb(self):
        """Initialize ChromaDB client and collection."""
        try:
            import chromadb
            from chromadb.config import Settings

            # Get configuration
            persist_dir = self.db_config.get('persist_directory', './data/chromadb')
            collection_name = self.db_config.get('collection_name', 'document_embeddings')
            distance_metric = self.db_config.get('distance_metric', 'cosine')

            # Create persist directory
            persist_path = Path(persist_dir)
            persist_path.mkdir(parents=True, exist_ok=True)

            # Initialize client
            self.client = chromadb.PersistentClient(
                path=str(persist_path),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )

            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=collection_name)
                self.logger.info(
                    f"Loaded existing collection '{collection_name}' "
                    f"with {self.collection.count()} documents"
                )
            except Exception:
                # Create new collection
                metadata = {"hnsw:space": distance_metric}
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata=metadata
                )
                self.logger.info(f"Created new collection '{collection_name}'")

        except ImportError:
            raise RuntimeError(
                "chromadb not available. Install with: pip install chromadb"
            )
        except Exception as e:
            raise RuntimeError(f"Failed to initialize ChromaDB: {e}")

    def process(self, doc: DocumentData) -> DocumentData:
        """Store document chunks and embeddings in ChromaDB.

        Args:
            doc: DocumentData with chunks and embeddings

        Returns:
            DocumentData with database IDs added
        """
        if not doc.chunks or not doc.embeddings:
            self.log_skip(f"{doc.file_path.name}: No chunks/embeddings to store")
            return doc

        if doc.processing_status == 'failed':
            self.log_skip(f"{doc.file_path.name}: Previous processing failed")
            return doc

        try:
            # Prepare data for ChromaDB
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for chunk in doc.chunks:
                # Generate unique ID
                chunk_id = str(uuid.uuid4())
                ids.append(chunk_id)

                # Add embedding
                embeddings.append(chunk['embedding'])

                # Add text
                documents.append(chunk['text'])

                # Prepare metadata (ChromaDB doesn't support nested dicts)
                metadata = self._flatten_metadata(chunk['metadata'])
                metadata['chunk_index'] = chunk['chunk_index']
                metadata['char_count'] = chunk['char_count']
                metadata['token_count'] = chunk['token_count']

                # Add OCR confidence if available
                if doc.ocr_confidence is not None:
                    metadata['ocr_confidence'] = float(doc.ocr_confidence)

                metadatas.append(metadata)

            # Store in ChromaDB
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            # Update document with database IDs
            for chunk, chunk_id in zip(doc.chunks, ids):
                chunk['db_id'] = chunk_id

            doc.processing_status = 'completed'
            self.log_success(
                f"Stored {len(ids)} chunks from {doc.file_path.name} in ChromaDB"
            )

        except Exception as e:
            self.log_error(f"Database storage failed for {doc.file_path.name}", e)
            doc.processing_status = 'failed'
            doc.errors.append(f"Database error: {str(e)}")

        return doc

    def _flatten_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Flatten nested metadata for ChromaDB.

        ChromaDB requires flat metadata dictionaries.

        Args:
            metadata: Possibly nested metadata dictionary

        Returns:
            Flattened metadata dictionary
        """
        flat = {}

        for key, value in metadata.items():
            if isinstance(value, (str, int, float, bool)):
                flat[key] = value
            elif isinstance(value, list):
                # Convert lists to comma-separated strings
                if all(isinstance(v, str) for v in value):
                    flat[key] = ', '.join(value)
            elif value is None:
                continue  # Skip None values
            else:
                # Convert other types to string
                flat[key] = str(value)

        return flat

    def query(
        self,
        query_text: Optional[str] = None,
        query_embedding: Optional[List[float]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Query the vector database.

        Args:
            query_text: Text query (will be embedded)
            query_embedding: Pre-computed embedding vector
            n_results: Number of results to return
            where: Metadata filter (e.g., {'source_file': 'doc.pdf'})
            where_document: Full-text filter (e.g., {'$contains': 'keyword'})

        Returns:
            Dictionary with query results
        """
        if query_text is None and query_embedding is None:
            raise ValueError("Either query_text or query_embedding must be provided")

        try:
            if query_text:
                # Use ChromaDB's built-in query (requires embedding function)
                # For now, assume query_embedding is provided
                raise NotImplementedError(
                    "Text query requires embedding function. "
                    "Please provide query_embedding instead."
                )

            results = self.collection.query(
                query_embeddings=[query_embedding] if query_embedding else None,
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=['documents', 'metadatas', 'distances']
            )

            self.logger.info(f"Query returned {len(results['ids'][0])} results")
            return results

        except Exception as e:
            self.logger.error(f"Query failed: {e}")
            raise

    def delete_by_source(self, source_file: str) -> int:
        """Delete all chunks from a specific source file.

        Args:
            source_file: Source file path

        Returns:
            Number of chunks deleted
        """
        try:
            # Query for all chunks from this source
            results = self.collection.get(
                where={'source_file': source_file},
                include=['metadatas']
            )

            if results['ids']:
                self.collection.delete(ids=results['ids'])
                count = len(results['ids'])
                self.logger.info(f"Deleted {count} chunks from {source_file}")
                return count
            else:
                self.logger.info(f"No chunks found for {source_file}")
                return 0

        except Exception as e:
            self.logger.error(f"Failed to delete chunks: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics.

        Returns:
            Dictionary with statistics
        """
        try:
            total_count = self.collection.count()

            # Get unique source files
            all_metadata = self.collection.get(include=['metadatas'])
            source_files = set()

            for metadata in all_metadata['metadatas']:
                if 'source_file' in metadata:
                    source_files.add(metadata['source_file'])

            stats = {
                'total_chunks': total_count,
                'unique_sources': len(source_files),
                'collection_name': self.collection.name,
            }

            return stats

        except Exception as e:
            self.logger.error(f"Failed to get stats: {e}")
            return {}

    def reset_database(self):
        """Delete all data from the collection.

        WARNING: This is irreversible!
        """
        try:
            # Delete collection
            self.client.delete_collection(self.collection.name)

            # Recreate collection
            collection_name = self.db_config.get('collection_name', 'document_embeddings')
            distance_metric = self.db_config.get('distance_metric', 'cosine')

            metadata = {"hnsw:space": distance_metric}
            self.collection = self.client.create_collection(
                name=collection_name,
                metadata=metadata
            )

            self.logger.warning("Database reset: all data deleted")

        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            raise

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

        # Log batch statistics
        total_chunks = sum(len(doc.chunks) for doc in processed if doc.chunks)
        self.logger.info(
            f"Batch processed {len(documents)} documents, "
            f"{total_chunks} total chunks stored"
        )

        return processed
