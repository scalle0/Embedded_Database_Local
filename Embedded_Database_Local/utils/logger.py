"""Logging utility for the document processing system."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional


class Logger:
    """Centralized logging configuration."""

    _instances = {}

    @classmethod
    def get_logger(cls, name: str, config: dict = None) -> logging.Logger:
        """Get or create a logger instance.

        Args:
            name: Logger name (typically __name__ of the module)
            config: Optional logging configuration dict

        Returns:
            Configured logger instance
        """
        if name in cls._instances:
            return cls._instances[name]

        logger = logging.getLogger(name)

        # Default config if none provided
        if config is None:
            config = {
                'level': 'INFO',
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                'file': None,
                'max_bytes': 10485760,  # 10MB
                'backup_count': 5
            }

        # Set level
        level = getattr(logging, config.get('level', 'INFO').upper())
        logger.setLevel(level)

        # Remove existing handlers
        logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(config.get('format'))
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (if specified)
        log_file = config.get('file')
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)

            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=config.get('max_bytes', 10485760),
                backupCount=config.get('backup_count', 5)
            )
            file_handler.setLevel(level)
            file_handler.setFormatter(console_formatter)
            logger.addHandler(file_handler)

        # Prevent propagation to root logger
        logger.propagate = False

        cls._instances[name] = logger
        return logger


def setup_logging(config: dict) -> logging.Logger:
    """Setup logging for the application.

    Args:
        config: Logging configuration from config.yaml

    Returns:
        Root logger instance
    """
    return Logger.get_logger('document_processor', config)
