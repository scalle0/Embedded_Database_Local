"""Base agent class for all processing agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pathlib import Path
import logging


class BaseAgent(ABC):
    """Abstract base class for all processing agents."""

    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        """Initialize base agent.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }

    @abstractmethod
    def process(self, input_data: Any) -> Any:
        """Process input data.

        Args:
            input_data: Input to process (format depends on agent type)

        Returns:
            Processed output (format depends on agent type)
        """
        pass

    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics.

        Returns:
            Dictionary with processed, failed, skipped counts
        """
        return self.stats.copy()

    def reset_stats(self):
        """Reset processing statistics."""
        self.stats = {
            'processed': 0,
            'failed': 0,
            'skipped': 0
        }

    def log_success(self, message: str):
        """Log successful processing."""
        self.logger.info(message)
        self.stats['processed'] += 1

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log error."""
        if exception:
            self.logger.error(f"{message}: {str(exception)}", exc_info=True)
        else:
            self.logger.error(message)
        self.stats['failed'] += 1

    def log_skip(self, message: str):
        """Log skipped item."""
        self.logger.info(f"Skipped: {message}")
        self.stats['skipped'] += 1


class DocumentData:
    """Data structure for passing document information between agents."""

    def __init__(
        self,
        file_path: Path,
        file_type: str,
        metadata: Optional[Dict[str, Any]] = None,
        content: Optional[str] = None,
        raw_data: Optional[bytes] = None
    ):
        """Initialize document data.

        Args:
            file_path: Path to source file
            file_type: File extension (e.g., 'pdf', 'docx')
            metadata: Document metadata (author, date, etc.)
            content: Extracted text content
            raw_data: Raw file bytes (for images, PDFs)
        """
        self.file_path = Path(file_path)
        self.file_type = file_type.lower().lstrip('.')
        self.metadata = metadata or {}
        self.content = content
        self.raw_data = raw_data

        # Processing metadata
        self.processing_status = 'pending'  # pending, processing, completed, failed
        self.ocr_confidence = None
        self.chunks = []  # Text chunks for embedding
        self.embeddings = []  # Vector embeddings
        self.errors = []  # Error messages

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            'file_path': str(self.file_path),
            'file_type': self.file_type,
            'metadata': self.metadata,
            'content_length': len(self.content) if self.content else 0,
            'processing_status': self.processing_status,
            'ocr_confidence': self.ocr_confidence,
            'num_chunks': len(self.chunks),
            'num_embeddings': len(self.embeddings),
            'errors': self.errors
        }

    def __repr__(self) -> str:
        return f"DocumentData(file={self.file_path.name}, type={self.file_type}, status={self.processing_status})"
