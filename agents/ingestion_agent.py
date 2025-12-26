"""Document ingestion agent - handles file discovery and initial processing."""

import hashlib
import mimetypes
from pathlib import Path
from typing import List, Optional, Dict, Any
import magic  # python-magic for file type detection
from datetime import datetime

from .base_agent import BaseAgent, DocumentData


class IngestionAgent(BaseAgent):
    """Agent responsible for discovering and validating input documents."""

    def __init__(self, config: Dict[str, Any], logger=None):
        """Initialize ingestion agent.

        Args:
            config: Configuration dictionary
            logger: Optional logger instance
        """
        super().__init__(config, logger)
        self.supported_formats = set(
            config.get('pipeline', {}).get('supported_formats', [])
        )
        self.input_dir = Path(config.get('directories', {}).get('input', './data/input'))
        self.processed_dir = Path(config.get('directories', {}).get('processed', './data/processed'))
        self.failed_dir = Path(config.get('directories', {}).get('failed', './data/failed'))

        # Duplicate detection
        self.skip_duplicates = config.get('pipeline', {}).get('skip_duplicates', True)
        self.processed_hashes = set()

        # Create directories
        self.input_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.failed_dir.mkdir(parents=True, exist_ok=True)

        # Initialize magic for file type detection
        try:
            self.magic = magic.Magic(mime=True)
        except Exception as e:
            self.logger.warning(f"Could not initialize python-magic: {e}. Using extension-based detection.")
            self.magic = None

    def process(self, input_path: Optional[Path] = None) -> List[DocumentData]:
        """Discover and validate documents for processing.

        Args:
            input_path: Optional specific file/directory to process.
                       If None, scans the configured input directory.

        Returns:
            List of DocumentData objects ready for processing
        """
        if input_path is None:
            input_path = self.input_dir

        input_path = Path(input_path)

        if input_path.is_file():
            documents = [self._process_file(input_path)]
        elif input_path.is_dir():
            documents = self._scan_directory(input_path)
        else:
            self.log_error(f"Invalid path: {input_path}")
            return []

        # Filter out None values (invalid files)
        documents = [doc for doc in documents if doc is not None]

        self.logger.info(
            f"Ingestion complete: {len(documents)} documents ready, "
            f"{self.stats['skipped']} skipped, {self.stats['failed']} failed"
        )

        return documents

    def _scan_directory(self, directory: Path) -> List[DocumentData]:
        """Recursively scan directory for supported files.

        Args:
            directory: Directory to scan

        Returns:
            List of DocumentData objects
        """
        documents = []

        for file_path in directory.rglob('*'):
            if file_path.is_file():
                doc = self._process_file(file_path)
                if doc is not None:
                    documents.append(doc)

        return documents

    def _process_file(self, file_path: Path) -> Optional[DocumentData]:
        """Process a single file.

        Args:
            file_path: Path to file

        Returns:
            DocumentData object or None if invalid/duplicate
        """
        # Check if supported format
        file_ext = file_path.suffix.lower()
        if file_ext not in self.supported_formats:
            self.log_skip(f"{file_path.name}: Unsupported format {file_ext}")
            return None

        # Check for duplicates
        if self.skip_duplicates:
            file_hash = self._compute_hash(file_path)
            if file_hash in self.processed_hashes:
                self.log_skip(f"{file_path.name}: Duplicate (hash: {file_hash[:8]}...)")
                return None
            self.processed_hashes.add(file_hash)

        # Detect file type
        file_type = self._detect_file_type(file_path)

        # Extract basic metadata
        metadata = self._extract_metadata(file_path, file_hash if self.skip_duplicates else None)

        # Load raw data for files that need binary reading
        # (images, PDFs, and Office documents)
        raw_data = None
        if file_ext in {'.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.pdf',
                        '.docx', '.doc', '.msg', '.eml'}:
            try:
                with open(file_path, 'rb') as f:
                    raw_data = f.read()
            except Exception as e:
                self.log_error(f"Failed to read {file_path.name}", e)
                return None

        # Create DocumentData
        doc = DocumentData(
            file_path=file_path,
            file_type=file_type,
            metadata=metadata,
            raw_data=raw_data
        )

        self.log_success(f"Ingested: {file_path.name} ({file_type})")
        return doc

    def _detect_file_type(self, file_path: Path) -> str:
        """Detect file type using magic or extension.

        Args:
            file_path: Path to file

        Returns:
            File type string
        """
        # Try magic first
        if self.magic:
            try:
                mime = self.magic.from_file(str(file_path))
                if 'pdf' in mime:
                    return 'pdf'
                elif 'word' in mime or 'officedocument' in mime:
                    return 'docx'
                elif 'image' in mime:
                    return 'image'
                elif 'text' in mime:
                    return 'text'
            except Exception as e:
                self.logger.debug(f"Magic detection failed for {file_path.name}: {e}")

        # Fallback to extension
        ext = file_path.suffix.lower().lstrip('.')
        return ext

    def _extract_metadata(self, file_path: Path, file_hash: Optional[str] = None) -> Dict[str, Any]:
        """Extract basic file metadata.

        Args:
            file_path: Path to file
            file_hash: Optional file hash

        Returns:
            Metadata dictionary
        """
        stat = file_path.stat()

        metadata = {
            'source_file': str(file_path),
            'filename': file_path.name,
            'file_size': stat.st_size,
            'created_date': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified_date': datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }

        if file_hash:
            metadata['file_hash'] = file_hash

        return metadata

    def _compute_hash(self, file_path: Path, chunk_size: int = 8192) -> str:
        """Compute SHA256 hash of file.

        Args:
            file_path: Path to file
            chunk_size: Chunk size for reading large files

        Returns:
            Hexadecimal hash string
        """
        sha256 = hashlib.sha256()

        try:
            with open(file_path, 'rb') as f:
                while chunk := f.read(chunk_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except Exception as e:
            self.logger.warning(f"Failed to compute hash for {file_path.name}: {e}")
            return ""

    def load_processed_hashes(self, hash_file: Optional[Path] = None):
        """Load previously processed file hashes from disk.

        Args:
            hash_file: Path to hash file. If None, uses processed_dir/.hashes
        """
        if hash_file is None:
            hash_file = self.processed_dir / '.hashes'

        if hash_file.exists():
            try:
                with open(hash_file, 'r') as f:
                    self.processed_hashes = set(line.strip() for line in f if line.strip())
                self.logger.info(f"Loaded {len(self.processed_hashes)} processed file hashes")
            except Exception as e:
                self.logger.warning(f"Failed to load hash file: {e}")

    def save_processed_hashes(self, hash_file: Optional[Path] = None):
        """Save processed file hashes to disk.

        Args:
            hash_file: Path to hash file. If None, uses processed_dir/.hashes
        """
        if hash_file is None:
            hash_file = self.processed_dir / '.hashes'

        try:
            with open(hash_file, 'w') as f:
                for h in sorted(self.processed_hashes):
                    f.write(f"{h}\n")
            self.logger.info(f"Saved {len(self.processed_hashes)} file hashes")
        except Exception as e:
            self.logger.error(f"Failed to save hash file: {e}")
