"""Memory monitoring utilities for large-scale processing."""

import psutil
import gc
import logging
from typing import Optional


class MemoryMonitor:
    """Monitor and manage memory usage during processing."""

    def __init__(self, logger: Optional[logging.Logger] = None, max_memory_percent: float = 80.0):
        """Initialize memory monitor.

        Args:
            logger: Optional logger instance
            max_memory_percent: Maximum memory usage percentage before warning
        """
        self.logger = logger or logging.getLogger(__name__)
        self.max_memory_percent = max_memory_percent
        self.process = psutil.Process()

    def get_memory_usage(self) -> dict:
        """Get current memory usage statistics.

        Returns:
            Dictionary with memory statistics
        """
        mem_info = self.process.memory_info()
        virtual_mem = psutil.virtual_memory()

        return {
            'rss_mb': mem_info.rss / 1024 / 1024,  # Resident Set Size in MB
            'vms_mb': mem_info.vms / 1024 / 1024,  # Virtual Memory Size in MB
            'percent': self.process.memory_percent(),
            'available_mb': virtual_mem.available / 1024 / 1024,
            'total_mb': virtual_mem.total / 1024 / 1024,
            'system_percent': virtual_mem.percent
        }

    def check_memory_usage(self, force_gc: bool = False) -> bool:
        """Check if memory usage is within acceptable limits.

        Args:
            force_gc: Whether to force garbage collection

        Returns:
            True if memory usage is OK, False if exceeding limits
        """
        usage = self.get_memory_usage()

        if usage['system_percent'] > self.max_memory_percent:
            self.logger.warning(
                f"High memory usage: {usage['system_percent']:.1f}% "
                f"(RSS: {usage['rss_mb']:.1f} MB)"
            )

            if force_gc:
                self.logger.info("Running garbage collection...")
                gc.collect()
                new_usage = self.get_memory_usage()
                self.logger.info(
                    f"After GC: {new_usage['system_percent']:.1f}% "
                    f"(RSS: {new_usage['rss_mb']:.1f} MB)"
                )

            return False

        return True

    def log_memory_usage(self, context: str = ""):
        """Log current memory usage.

        Args:
            context: Optional context string for the log message
        """
        usage = self.get_memory_usage()
        msg = (
            f"Memory usage"
            f"{' (' + context + ')' if context else ''}: "
            f"{usage['system_percent']:.1f}% "
            f"(Process: {usage['rss_mb']:.1f} MB, "
            f"Available: {usage['available_mb']:.1f} MB)"
        )
        self.logger.info(msg)

    def clear_memory(self, aggressive: bool = False):
        """Attempt to free memory.

        Args:
            aggressive: Whether to use aggressive cleanup
        """
        self.logger.info("Clearing memory...")

        # Run garbage collection
        if aggressive:
            # Multiple GC passes for aggressive cleanup
            for i in range(3):
                collected = gc.collect()
                self.logger.debug(f"GC pass {i+1}: collected {collected} objects")
        else:
            collected = gc.collect()
            self.logger.debug(f"GC: collected {collected} objects")

        usage = self.get_memory_usage()
        self.logger.info(
            f"After cleanup: {usage['system_percent']:.1f}% "
            f"(RSS: {usage['rss_mb']:.1f} MB)"
        )
