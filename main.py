#!/usr/bin/env python3
"""Main entry point for document processing system."""

import sys
import argparse
from pathlib import Path

from utils.config_loader import get_config
from utils.logger import setup_logging
from agents.orchestrator import Orchestrator


def process_documents(
    input_path: str = None,
    config_path: str = None,
    parallel: bool = True,
    reset_db: bool = False
):
    """Process documents through the pipeline.

    Args:
        input_path: Path to input file or directory
        config_path: Path to config file
        parallel: Use parallel processing
        reset_db: Reset database before processing
    """
    # Load configuration
    config = get_config(config_path)

    try:
        config.validate()
    except ValueError as e:
        print(f"Configuration error: {e}")
        print("\nPlease set your GEMINI_API_KEY environment variable or update config.yaml")
        sys.exit(1)

    # Setup logging
    log_config = config.get('logging', {})
    logger = setup_logging(log_config)

    logger.info("Document Processing System Starting...")
    logger.info(f"Configuration loaded from: {config.config_path}")

    # Initialize orchestrator
    orchestrator = Orchestrator(config.get_all(), logger)

    # Reset database if requested
    if reset_db:
        logger.warning("Resetting database...")
        confirm = input("This will delete all data! Type 'yes' to confirm: ")
        if confirm.lower() == 'yes':
            orchestrator.database_agent.reset_database()
            logger.info("Database reset complete")
        else:
            logger.info("Database reset cancelled")
            return

    # Process documents
    input_path = Path(input_path) if input_path else None
    stats = orchestrator.process(input_path=input_path, parallel=parallel)

    logger.info("Processing complete!")

    return stats


def main():
    """Main entry point with CLI argument parsing."""
    parser = argparse.ArgumentParser(
        description="Multi-agent document processing and embedding system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process all documents in configured input directory
  python main.py

  # Process specific file
  python main.py --input /path/to/document.pdf

  # Process directory
  python main.py --input /path/to/documents/

  # Use sequential processing (slower but more stable)
  python main.py --no-parallel

  # Reset database before processing
  python main.py --reset-db

  # Use custom config file
  python main.py --config /path/to/config.yaml

  # Interactive search
  python query_interface.py
        """
    )

    parser.add_argument(
        '--input', '-i',
        type=str,
        help='Path to input file or directory (default: configured input directory)'
    )

    parser.add_argument(
        '--config', '-c',
        type=str,
        help='Path to configuration file (default: config/config.yaml)'
    )

    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help='Disable parallel processing'
    )

    parser.add_argument(
        '--reset-db',
        action='store_true',
        help='Reset database before processing (WARNING: deletes all data)'
    )

    args = parser.parse_args()

    # Run processing
    try:
        process_documents(
            input_path=args.input,
            config_path=args.config,
            parallel=not args.no_parallel,
            reset_db=args.reset_db
        )
    except KeyboardInterrupt:
        print("\n\nProcessing interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
