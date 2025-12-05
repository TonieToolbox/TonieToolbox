#!/usr/bin/env python3
"""
Platform-agnostic parallel execution for file processing.

Supports both CLI (ThreadPoolExecutor) and GUI (QtThreadManager) contexts.
This module provides a unified interface for parallel batch processing that works
seamlessly in both command-line and GUI environments.
"""

from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from typing import Callable, List, Dict, Any, Optional, TypeVar, Generic
from pathlib import Path

from ...utils.logging import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class ParallelExecutor(ABC, Generic[T]):
    """
    Abstract parallel executor for batch processing.
    
    Provides unified interface for parallel execution in both CLI
    and GUI contexts, with progress tracking and error handling.
    
    This abstraction allows the same processing logic to work in both
    CLI (using ThreadPoolExecutor) and GUI (using QtThreadManager) contexts
    without code duplication.
    
    Example:
        >>> executor = ThreadPoolParallelExecutor(max_workers=4)
        >>> 
        >>> def process_file(file_path):
        ...     # Process file
        ...     return {'status': 'completed', 'path': file_path}
        >>> 
        >>> results = executor.execute_batch(
        ...     task=process_file,
        ...     items=['file1.mp3', 'file2.mp3', 'file3.mp3'],
        ...     on_progress=lambda completed, total: print(f"{completed}/{total}"),
        ...     continue_on_error=True
        ... )
        >>> 
        >>> executor.shutdown()
    """
    
    @abstractmethod
    def execute_batch(
        self,
        task: Callable[[T], Dict[str, Any]],
        items: List[T],
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_item_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        continue_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute task on all items in parallel.
        
        Args:
            task: Function to execute on each item (must return dict)
            items: List of items to process
            on_progress: Progress callback receiving (completed_count, total_count)
            on_item_complete: Called when each item completes with result dict
            continue_on_error: Continue processing remaining items if one fails
            
        Returns:
            List of result dictionaries from all items
        """
        pass
    
    @abstractmethod
    def shutdown(self, timeout: int = 5) -> None:
        """
        Shutdown executor and cleanup resources.
        
        Args:
            timeout: Maximum seconds to wait for shutdown
        """
        pass


class ThreadPoolParallelExecutor(ParallelExecutor[T]):
    """
    Thread pool based parallel executor for CLI usage.
    
    Uses concurrent.futures.ThreadPoolExecutor for parallel processing.
    Suitable for CLI batch operations where GUI event loop is not needed.
    Since FFmpeg operations run as subprocesses, ThreadPoolExecutor provides
    effective parallelism despite Python's GIL.
    
    Example:
        >>> executor = ThreadPoolParallelExecutor(max_workers=4)
        >>> 
        >>> def convert_folder(folder_info):
        ...     # Convert all audio files in folder to TAF
        ...     return {'status': 'completed', 'folder': folder_info['name']}
        >>> 
        >>> folders = [{'name': 'Album1', 'path': '/music/album1'}, ...]
        >>> results = executor.execute_batch(
        ...     task=convert_folder,
        ...     items=folders,
        ...     on_progress=lambda done, total: print(f"Progress: {done}/{total}"),
        ...     continue_on_error=True
        ... )
        >>> 
        >>> successful = [r for r in results if r['status'] == 'completed']
        >>> print(f"Converted {len(successful)} folders")
        >>> 
        >>> executor.shutdown()
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize thread pool executor.
        
        Args:
            max_workers: Maximum number of parallel worker threads
        """
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        logger.info(f"Thread pool executor initialized with {max_workers} workers")
    
    def execute_batch(
        self,
        task: Callable[[T], Dict[str, Any]],
        items: List[T],
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_item_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        continue_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """Execute batch processing with thread pool."""
        
        if not items:
            logger.debug("No items to process")
            return []
        
        total_items = len(items)
        completed_items = 0
        results = []
        
        logger.info(f"Starting batch processing of {total_items} items with {self.max_workers} workers")
        
        # Submit all tasks
        future_to_item = {
            self._executor.submit(task, item): item
            for item in items
        }
        
        # Process as completed (not in order - faster!)
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            
            try:
                result = future.result()
                results.append(result)
                
                completed_items += 1
                
                logger.debug(f"Item completed ({completed_items}/{total_items}): {result.get('status', 'unknown')}")
                
                # Notify progress
                if on_progress:
                    on_progress(completed_items, total_items)
                
                # Notify item completion
                if on_item_complete:
                    on_item_complete(result)
                    
            except Exception as e:
                logger.error(f"Task failed for item {item}: {e}")
                
                # Add failed result
                error_result = {
                    'status': 'failed',
                    'item': str(item) if not isinstance(item, dict) else item.get('name', str(item)),
                    'error': str(e)
                }
                results.append(error_result)
                
                completed_items += 1
                
                if on_progress:
                    on_progress(completed_items, total_items)
                
                if not continue_on_error:
                    logger.warning("Cancelling remaining tasks due to error")
                    # Cancel pending futures
                    for pending_future in future_to_item:
                        if not pending_future.done():
                            pending_future.cancel()
                    break
        
        logger.info(f"Batch processing complete: {completed_items}/{total_items} items processed")
        return results
    
    def shutdown(self, timeout: int = 5) -> None:
        """Shutdown thread pool executor."""
        logger.info("Shutting down thread pool executor...")
        try:
            self._executor.shutdown(wait=True)
            logger.info("Thread pool executor shutdown completed")
        except Exception as e:
            logger.error(f"Error shutting down executor: {e}")


class QtParallelExecutor(ParallelExecutor[T]):
    """
    Qt-based parallel executor for GUI usage.
    
    Uses QtThreadManager for parallel processing with proper Qt signal/slot
    integration for progress updates in GUI. Progress callbacks are automatically
    scheduled on the main Qt event loop thread to safely update UI elements.
    
    Example:
        >>> from TonieToolbox.core.gui.utils import QtThreadManager
        >>> 
        >>> qt_thread_mgr = QtThreadManager(max_workers=4)
        >>> executor = QtParallelExecutor(qt_thread_mgr, max_workers=4)
        >>> 
        >>> def convert_folder(folder_info):
        ...     # Convert folder (runs in worker thread)
        ...     return {'status': 'completed', 'folder': folder_info['name']}
        >>> 
        >>> def update_progress_bar(completed, total):
        ...     # This will be called on main thread, safe for GUI updates
        ...     progress_bar.setValue(int(completed / total * 100))
        >>> 
        >>> def update_file_list(result):
        ...     # This will be called on main thread
        ...     file_list.addItem(result['folder'])
        >>> 
        >>> # Run in background thread to not block GUI
        >>> qt_thread_mgr.run_in_background(
        ...     executor.execute_batch,
        ...     convert_folder,
        ...     folders,
        ...     on_progress=update_progress_bar,
        ...     on_item_complete=update_file_list
        ... )
    """
    
    def __init__(self, qt_thread_manager, max_workers: int = 4):
        """
        Initialize Qt parallel executor.
        
        Args:
            qt_thread_manager: QtThreadManager instance from GUI
            max_workers: Maximum number of parallel workers
        """
        self.thread_manager = qt_thread_manager
        self.max_workers = max_workers
        logger.info(f"Qt parallel executor initialized with {max_workers} workers")
    
    def execute_batch(
        self,
        task: Callable[[T], Dict[str, Any]],
        items: List[T],
        on_progress: Optional[Callable[[int, int], None]] = None,
        on_item_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        continue_on_error: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Execute batch processing with Qt threads.
        
        Note: For GUI usage, this should typically be called from a background thread
        via QtThreadManager.run_in_background() to avoid blocking the GUI event loop.
        Progress and completion callbacks are automatically scheduled on the main thread.
        """
        
        if not items:
            logger.debug("No items to process")
            return []
        
        total_items = len(items)
        completed_items = [0]  # Mutable list for closure capture
        results = []
        errors = []
        
        logger.info(f"Starting Qt batch processing of {total_items} items")
        
        # Use thread pool from QtThreadManager
        future_to_item = {
            self.thread_manager.run_in_thread_pool(task, item): item
            for item in items
        }
        
        # Process as completed
        for future in as_completed(future_to_item):
            item = future_to_item[future]
            
            try:
                result = future.result()
                results.append(result)
                
                completed_items[0] += 1
                current_completed = completed_items[0]  # Capture for closure
                
                logger.debug(f"Item completed ({current_completed}/{total_items})")
                
                # Schedule progress callback on main thread
                if on_progress:
                    self.thread_manager.schedule_ui_update(
                        lambda: on_progress(current_completed, total_items),
                        delay_ms=0
                    )
                
                # Schedule completion callback on main thread
                if on_item_complete:
                    # Capture result in closure to avoid late binding issues
                    result_copy = result.copy() if isinstance(result, dict) else result
                    self.thread_manager.schedule_ui_update(
                        lambda r=result_copy: on_item_complete(r),
                        delay_ms=0
                    )
                    
            except Exception as e:
                logger.error(f"Task failed for item {item}: {e}")
                errors.append(e)
                
                error_result = {
                    'status': 'failed',
                    'item': str(item) if not isinstance(item, dict) else item.get('name', str(item)),
                    'error': str(e)
                }
                results.append(error_result)
                
                completed_items[0] += 1
                current_completed = completed_items[0]
                
                if on_progress:
                    self.thread_manager.schedule_ui_update(
                        lambda: on_progress(current_completed, total_items),
                        delay_ms=0
                    )
                
                if not continue_on_error:
                    logger.warning("Cancelling remaining tasks due to error")
                    # Cancel remaining
                    for pending_future in future_to_item:
                        if not pending_future.done():
                            pending_future.cancel()
                    break
        
        logger.info(f"Qt batch processing complete: {completed_items[0]}/{total_items} items")
        return results
    
    def shutdown(self, timeout: int = 5) -> None:
        """
        Shutdown not needed for Qt executor.
        
        QtThreadManager handles its own lifecycle and cleanup.
        This method is a no-op for compatibility with the ParallelExecutor interface.
        """
        pass  # QtThreadManager handles cleanup


def create_parallel_executor(
    max_workers: int = 4,
    qt_thread_manager = None
) -> ParallelExecutor:
    """
    Factory function to create appropriate parallel executor.
    
    Automatically selects between ThreadPoolExecutor (CLI) and QtThreadManager (GUI)
    based on whether a QtThreadManager instance is provided.
    
    Args:
        max_workers: Maximum number of parallel workers
        qt_thread_manager: Optional QtThreadManager instance for GUI context
        
    Returns:
        ParallelExecutor instance (QtParallelExecutor if qt_thread_manager provided,
        otherwise ThreadPoolParallelExecutor)
        
    Example:
        CLI usage::
        
            executor = create_parallel_executor(max_workers=4)
            # Returns ThreadPoolParallelExecutor
        
        GUI usage::
        
            from TonieToolbox.core.gui.utils import QtThreadManager
            
            qt_mgr = QtThreadManager(max_workers=4)
            executor = create_parallel_executor(max_workers=4, qt_thread_manager=qt_mgr)
            # Returns QtParallelExecutor
    """
    if qt_thread_manager is not None:
        logger.debug("Creating Qt parallel executor for GUI context")
        return QtParallelExecutor(qt_thread_manager, max_workers)
    else:
        logger.debug("Creating thread pool executor for CLI context")
        return ThreadPoolParallelExecutor(max_workers)
