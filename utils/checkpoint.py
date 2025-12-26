"""Checkpoint system for resumable processing."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime


class CheckpointManager:
    """Manage processing checkpoints for crash recovery."""

    def __init__(
        self,
        checkpoint_file: Path,
        logger: Optional[logging.Logger] = None
    ):
        """Initialize checkpoint manager.

        Args:
            checkpoint_file: Path to checkpoint file
            logger: Optional logger instance
        """
        self.checkpoint_file = Path(checkpoint_file)
        self.logger = logger or logging.getLogger(__name__)
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)

    def save_checkpoint(
        self,
        processed_files: List[str],
        current_batch: int,
        total_batches: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Save checkpoint to disk.

        Args:
            processed_files: List of successfully processed file paths
            current_batch: Current batch number
            total_batches: Total number of batches
            metadata: Additional metadata to save
        """
        checkpoint = {
            'timestamp': datetime.now().isoformat(),
            'processed_files': processed_files,
            'current_batch': current_batch,
            'total_batches': total_batches,
            'metadata': metadata or {}
        }

        try:
            with open(self.checkpoint_file, 'w') as f:
                json.dump(checkpoint, f, indent=2)

            self.logger.info(
                f"Checkpoint saved: batch {current_batch}/{total_batches}, "
                f"{len(processed_files)} files processed"
            )

        except Exception as e:
            self.logger.error(f"Failed to save checkpoint: {e}")

    def load_checkpoint(self) -> Optional[Dict[str, Any]]:
        """Load checkpoint from disk.

        Returns:
            Checkpoint data or None if no checkpoint exists
        """
        if not self.checkpoint_file.exists():
            self.logger.info("No checkpoint file found")
            return None

        try:
            with open(self.checkpoint_file, 'r') as f:
                checkpoint = json.load(f)

            self.logger.info(
                f"Checkpoint loaded: batch {checkpoint['current_batch']}/"
                f"{checkpoint['total_batches']}, "
                f"{len(checkpoint['processed_files'])} files already processed"
            )

            return checkpoint

        except Exception as e:
            self.logger.error(f"Failed to load checkpoint: {e}")
            return None

    def clear_checkpoint(self):
        """Clear checkpoint file."""
        try:
            if self.checkpoint_file.exists():
                self.checkpoint_file.unlink()
                self.logger.info("Checkpoint cleared")
        except Exception as e:
            self.logger.error(f"Failed to clear checkpoint: {e}")

    def get_processed_files(self) -> List[str]:
        """Get list of already processed files from checkpoint.

        Returns:
            List of processed file paths
        """
        checkpoint = self.load_checkpoint()
        if checkpoint:
            return checkpoint.get('processed_files', [])
        return []
