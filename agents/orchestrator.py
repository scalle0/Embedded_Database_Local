"""Orchestrator agent - coordinates the document processing pipeline."""

from pathlib import Path
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import gc

from .base_agent import BaseAgent, DocumentData
from .ingestion_agent import IngestionAgent
from .ocr_agent import OCRAgent
from .extraction_agent import ExtractionAgent
from .embedding_agent import EmbeddingAgent
from .database_agent import DatabaseAgent

# Import memory monitoring and checkpoint utilities
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from utils.memory_monitor import MemoryMonitor
from utils.checkpoint import CheckpointManager


class Orchestrator(BaseAgent):
    """Main orchestrator that coordinates all processing agents."""

    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize orchestrator.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        self.pipeline_config = config.get('pipeline', {})

        # Initialize all agents
        self.logger.info("Initializing processing agents...")

        self.ingestion_agent = IngestionAgent(config, logger)
        self.ocr_agent = OCRAgent(config, logger)
        self.extraction_agent = ExtractionAgent(config, logger)
        self.embedding_agent = EmbeddingAgent(config, logger)
        self.database_agent = DatabaseAgent(config, logger)

        # Load embedding cache if it exists
        self.embedding_agent.load_cache()

        # Load processed hashes if they exist
        self.ingestion_agent.load_processed_hashes()

        # Initialize memory monitor
        max_memory = config.get('memory', {}).get('max_percent', 80.0)
        self.memory_monitor = MemoryMonitor(logger, max_memory_percent=max_memory)

        # Initialize checkpoint manager
        checkpoint_dir = Path(config.get('directories', {}).get('processed', './data/processed'))
        checkpoint_file = checkpoint_dir / '.checkpoint.json'
        self.checkpoint_manager = CheckpointManager(checkpoint_file, logger)

        # Streaming batch size for memory management
        self.stream_batch_size = config.get('memory', {}).get('stream_batch_size', 50)

        self.logger.info("All agents initialized successfully")

    def process(
        self,
        input_path: Optional[Path] = None,
        parallel: bool = True,
        resume: bool = True
    ) -> Dict[str, Any]:
        """Process documents through the complete pipeline with streaming and checkpoints.

        Args:
            input_path: Optional specific file/directory to process.
                       If None, uses configured input directory.
            parallel: Whether to use parallel processing
            resume: Whether to resume from checkpoint if available

        Returns:
            Dictionary with processing statistics
        """
        self.logger.info("=" * 80)
        self.logger.info("Starting document processing pipeline (Streaming Mode)")
        self.logger.info("=" * 80)

        # Log initial memory usage
        self.memory_monitor.log_memory_usage("startup")

        # Step 1: Ingestion
        self.logger.info("\n[1/5] Document Ingestion")
        all_documents = self.ingestion_agent.process(input_path)

        if not all_documents:
            self.logger.warning("No documents found to process")
            return self._get_final_stats()

        self.logger.info(f"Discovered {len(all_documents)} documents")

        # Check for checkpoint and filter already processed files
        processed_files = []
        start_batch = 0

        if resume:
            checkpoint = self.checkpoint_manager.load_checkpoint()
            if checkpoint:
                processed_files = checkpoint.get('processed_files', [])
                start_batch = checkpoint.get('current_batch', 0)

                # Filter out already processed documents
                processed_paths = set(processed_files)
                all_documents = [
                    doc for doc in all_documents
                    if str(doc.file_path) not in processed_paths
                ]

                self.logger.info(
                    f"Resuming from batch {start_batch}: "
                    f"{len(processed_files)} files already processed, "
                    f"{len(all_documents)} remaining"
                )

        # Process in streaming batches to manage memory
        total_batches = (len(all_documents) + self.stream_batch_size - 1) // self.stream_batch_size

        for batch_idx in range(0, len(all_documents), self.stream_batch_size):
            current_batch_num = (batch_idx // self.stream_batch_size) + 1 + start_batch

            batch = all_documents[batch_idx:batch_idx + self.stream_batch_size]

            self.logger.info(
                f"\n{'=' * 80}\n"
                f"Processing Batch {current_batch_num}/{total_batches + start_batch} "
                f"({len(batch)} documents)\n"
                f"{'=' * 80}"
            )

            # Memory check before processing
            self.memory_monitor.log_memory_usage(f"batch {current_batch_num} start")

            # Process batch through pipeline
            batch = self._process_batch(batch, parallel)

            # Save checkpoint after successful batch
            batch_processed_files = [
                str(doc.file_path) for doc in batch
                if doc.processing_status == 'completed'
            ]
            processed_files.extend(batch_processed_files)

            self.checkpoint_manager.save_checkpoint(
                processed_files=processed_files,
                current_batch=current_batch_num,
                total_batches=total_batches + start_batch
            )

            # Clear memory after batch
            del batch
            gc.collect()

            self.memory_monitor.log_memory_usage(f"batch {current_batch_num} end")

            # Check memory and force cleanup if needed
            if not self.memory_monitor.check_memory_usage(force_gc=True):
                self.logger.warning("High memory usage detected, running aggressive cleanup")
                self.memory_monitor.clear_memory(aggressive=True)

        # Step 5: Cleanup and Save State
        self.logger.info("\n[5/5] Cleanup & Saving State")
        self._cleanup_final()

        # Clear checkpoint after successful completion
        self.checkpoint_manager.clear_checkpoint()

        # Final statistics
        stats = self._get_final_stats()
        self._print_final_report(stats)

        return stats

    def _process_batch(
        self,
        documents: List[DocumentData],
        parallel: bool
    ) -> List[DocumentData]:
        """Process a batch of documents through the pipeline.

        Args:
            documents: List of documents to process
            parallel: Whether to use parallel processing

        Returns:
            Processed documents
        """
        # Step 2: Text Extraction & OCR
        self.logger.info(f"  [2/4] Extracting text from {len(documents)} documents")

        if parallel:
            documents = self._parallel_extract(documents)
        else:
            documents = self._sequential_extract(documents)

        # Step 3: Embedding Generation
        self.logger.info(f"  [3/4] Generating embeddings for {len(documents)} documents")

        if parallel:
            documents = self._parallel_embed(documents)
        else:
            documents = self._sequential_embed(documents)

        # Step 4: Database Storage
        self.logger.info(f"  [4/4] Storing {len(documents)} documents in database")

        if parallel:
            documents = self._parallel_store(documents)
        else:
            documents = self._sequential_store(documents)

        # Save state after each batch
        self.embedding_agent.save_cache()
        self.ingestion_agent.save_processed_hashes()

        return documents

    def _sequential_extract(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Extract text from documents sequentially.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        processed = []

        for doc in tqdm(documents, desc="Extracting"):
            # Determine if OCR or text extraction is needed
            if doc.file_type in {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'image'}:
                doc = self.ocr_agent.process(doc)
            elif doc.file_type == 'pdf':
                # Try text extraction first
                doc = self.extraction_agent.process(doc)
                # If requires OCR, apply it
                if doc.metadata.get('requires_ocr', False):
                    doc = self.ocr_agent.process(doc)
            else:
                doc = self.extraction_agent.process(doc)

            processed.append(doc)

        return processed

    def _parallel_extract(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Extract text from documents in parallel.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        max_workers = self.pipeline_config.get('max_workers', 4)
        processed = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for doc in documents:
                if doc.file_type in {'png', 'jpg', 'jpeg', 'tiff', 'bmp', 'image'}:
                    future = executor.submit(self.ocr_agent.process, doc)
                else:
                    future = executor.submit(self.extraction_agent.process, doc)

                futures[future] = doc

            # Collect results with progress bar
            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Extracting"
            ):
                try:
                    result = future.result()
                    processed.append(result)

                    # Handle PDFs that need OCR
                    if result.file_type == 'pdf' and result.metadata.get('requires_ocr', False):
                        ocr_future = executor.submit(self.ocr_agent.process, result)
                        ocr_result = ocr_future.result()
                        # Replace with OCR version
                        processed[-1] = ocr_result

                except Exception as e:
                    doc = futures[future]
                    self.logger.error(f"Extraction failed for {doc.file_path.name}: {e}")
                    doc.processing_status = 'failed'
                    doc.errors.append(f"Extraction error: {str(e)}")
                    processed.append(doc)

        return processed

    def _sequential_embed(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Generate embeddings sequentially.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        processed = []

        for doc in tqdm(documents, desc="Embedding"):
            doc = self.embedding_agent.process(doc)
            processed.append(doc)

        return processed

    def _parallel_embed(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Generate embeddings in parallel.

        Note: Gemini API has rate limits, so we use smaller batch size.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        # Use smaller batch for API calls
        batch_size = self.pipeline_config.get('batch_size', 10)
        processed = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]

            for doc in tqdm(batch, desc=f"Embedding batch {i // batch_size + 1}"):
                doc = self.embedding_agent.process(doc)
                processed.append(doc)

        return processed

    def _sequential_store(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Store documents in database sequentially.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        processed = []

        for doc in tqdm(documents, desc="Storing"):
            doc = self.database_agent.process(doc)
            processed.append(doc)

        return processed

    def _parallel_store(self, documents: List[DocumentData]) -> List[DocumentData]:
        """Store documents in database in parallel.

        Args:
            documents: List of DocumentData objects

        Returns:
            List of processed documents
        """
        max_workers = self.pipeline_config.get('max_workers', 4)
        processed = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.database_agent.process, doc): doc
                for doc in documents
            }

            for future in tqdm(
                as_completed(futures),
                total=len(futures),
                desc="Storing"
            ):
                try:
                    result = future.result()
                    processed.append(result)
                except Exception as e:
                    doc = futures[future]
                    self.logger.error(f"Database storage failed for {doc.file_path.name}: {e}")
                    doc.processing_status = 'failed'
                    doc.errors.append(f"Storage error: {str(e)}")
                    processed.append(doc)

        return processed

    def _cleanup_final(self):
        """Final cleanup and save state after all processing."""
        # Save embedding cache
        self.embedding_agent.save_cache()

        # Save processed file hashes
        self.ingestion_agent.save_processed_hashes()

        # Final memory cleanup
        self.memory_monitor.clear_memory(aggressive=True)
        self.memory_monitor.log_memory_usage("final cleanup")

    def _get_final_stats(self) -> Dict[str, Any]:
        """Get final processing statistics.

        Returns:
            Dictionary with statistics from all agents
        """
        db_stats = self.database_agent.get_stats()

        stats = {
            'ingestion': self.ingestion_agent.get_stats(),
            'ocr': self.ocr_agent.get_stats(),
            'extraction': self.extraction_agent.get_stats(),
            'embedding': self.embedding_agent.get_stats(),
            'database': self.database_agent.get_stats(),
            'database_totals': db_stats,
            'embedding_cache': {
                'cache_hits': self.embedding_agent.cache_hits,
                'cache_misses': self.embedding_agent.cache_misses,
                'cache_size': len(self.embedding_agent.embedding_cache)
            }
        }

        return stats

    def _print_final_report(self, stats: Dict[str, Any]):
        """Print final processing report.

        Args:
            stats: Statistics dictionary
        """
        self.logger.info("\n" + "=" * 80)
        self.logger.info("PROCESSING COMPLETE - FINAL REPORT")
        self.logger.info("=" * 80)

        # Agent statistics
        for agent_name, agent_stats in stats.items():
            if agent_name in {'ingestion', 'ocr', 'extraction', 'embedding', 'database'}:
                processed = agent_stats.get('processed', 0)
                failed = agent_stats.get('failed', 0)
                skipped = agent_stats.get('skipped', 0)

                self.logger.info(
                    f"{agent_name.capitalize():15s}: "
                    f"✓ {processed:4d}  ✗ {failed:4d}  ⊘ {skipped:4d}"
                )

        # Database totals
        db_totals = stats.get('database_totals', {})
        self.logger.info(f"\nDatabase: {db_totals.get('total_chunks', 0)} chunks from "
                        f"{db_totals.get('unique_sources', 0)} source files")

        # Cache stats
        cache = stats.get('embedding_cache', {})
        total_calls = cache.get('cache_hits', 0) + cache.get('cache_misses', 0)
        hit_rate = (cache.get('cache_hits', 0) / total_calls * 100) if total_calls > 0 else 0

        self.logger.info(
            f"Embedding cache: {cache.get('cache_size', 0)} entries, "
            f"{hit_rate:.1f}% hit rate"
        )

        self.logger.info("=" * 80)
