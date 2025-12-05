#!/usr/bin/env python3
"""
Threading utilities for PyQt6 GUI.
"""
import threading
from typing import Callable, Any, Optional, Dict
from concurrent.futures import ThreadPoolExecutor, Future

try:
    from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread, QMutex, QMutexLocker
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    QObject = object
    pyqtSignal = lambda: None
    QTimer = object
    QThread = object
    QMutex = object
    QMutexLocker = object

from TonieToolbox.core.utils import get_logger

logger = get_logger(__name__)


class QtWorkerSignals(QObject):
    """Signals for Qt worker threads."""
    
    finished = pyqtSignal()
    error = pyqtSignal(tuple)  # (exception_type, exception_value, traceback)
    result = pyqtSignal(object)
    progress = pyqtSignal(object)


class QtWorker(QObject):
    """
    Qt worker for running tasks in background threads.
    
    Wraps a callable function to run in a QThread, providing signals for
    result, error, and completion notification. This pattern prevents GUI
    freezing during long-running operations.
    
    Example:
        Run a long task without blocking the GUI::
        
            from TonieToolbox.core.gui.utils.threading import QtWorker
            from PyQt6.QtCore import QThread
            
            def process_file(file_path):
                # Long-running operation
                time.sleep(5)
                return f"Processed {file_path}"
            
            # Create worker and thread
            worker = QtWorker(process_file, '/path/to/file.taf')
            thread = QThread()
            worker.moveToThread(thread)
            
            # Connect signals
            worker.signals.result.connect(lambda result: print(f"Done: {result}"))
            worker.signals.error.connect(lambda err: print(f"Error: {err[1]}"))
            worker.signals.finished.connect(thread.quit)
            
            # Start processing
            thread.started.connect(worker.run)
            thread.start()
    """
    
    def __init__(self, fn: Callable, *args, **kwargs):
        """
        Initialize the worker.
        
        Args:
            fn: Function to run in background
            *args: Function arguments
            **kwargs: Function keyword arguments
        """
        super().__init__()
        
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = QtWorkerSignals()
    
    def run(self):
        """Run the worker task."""
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.signals.result.emit(result)
        except Exception as e:
            import traceback
            self.signals.error.emit((type(e), e, traceback.format_exc()))
        finally:
            self.signals.finished.emit()


class QtThreadManager(QObject):
    """
    Thread manager for PyQt6 applications.
    Provides safe threading utilities and worker management.
    
    This class simplifies running background tasks in Qt applications, handling
    thread creation, signal connections, and cleanup. It uses a thread pool
    to limit concurrent operations and prevent resource exhaustion.
    
    Example:
        Initialize and use thread manager::
        
            from TonieToolbox.core.gui.utils.threading import QtThreadManager
            
            # Create manager with max 4 concurrent workers
            thread_mgr = QtThreadManager(max_workers=4)
            
            def heavy_computation(data):
                # Long-running task
                result = process_large_dataset(data)
                return result
            
            def on_success(result):
                print(f"Computation complete: {result}")
                status_label.setText("Processing complete")
            
            def on_error(error):
                print(f"Error occurred: {error}")
                show_error_dialog(str(error))
            
            # Run in background
            thread_mgr.run_in_background(
                heavy_computation,
                large_data,
                on_result=on_success,
                on_error=on_error,
                on_finished=lambda: progress_bar.hide()
            )
        
        Convert audio file without blocking GUI::
        
            def convert_to_taf(input_path, output_path):
                converter = FFmpegConverter(logger, dependencies, event_bus)
                converter.convert_to_taf(input_path, output_path)
                return output_path
            
            def update_ui(output_path):
                result_label.setText(f"Converted: {output_path}")
                enable_play_button()
            
            thread_mgr.run_in_background(
                convert_to_taf,
                'input.mp3',
                'output.taf',
                on_result=update_ui,
                on_error=lambda e: show_error(f"Conversion failed: {e}")
            )
        
        Multiple concurrent tasks::
        
            # Process multiple files concurrently (max_workers limit applies)
            for file_path in audio_files:
                thread_mgr.run_in_background(
                    analyze_audio_file,
                    file_path,
                    on_result=lambda result: update_file_list(result)
                )
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the thread manager.
        
        Args:
            max_workers: Maximum number of worker threads
        """
        super().__init__()
        
        if not PYQT6_AVAILABLE:
            logger.warning("PyQt6 not available, thread manager will have limited functionality")
            max_workers = max_workers  # Keep for fallback implementation
        
        self.max_workers = max_workers
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._active_workers: Dict[str, QThread] = {}
        self._worker_counter = 0
        self._mutex = QMutex() if PYQT6_AVAILABLE else threading.RLock()
        
        logger.info(f"Qt thread manager initialized with {max_workers} workers")
    
    def run_in_background(self, task: Callable, *args, 
                         on_result: Optional[Callable] = None,
                         on_error: Optional[Callable] = None,
                         on_finished: Optional[Callable] = None,
                         **kwargs) -> Optional[QThread]:
        """
        Run a task in a background Qt thread.
        
        Creates a worker thread to execute the task, connecting provided callbacks
        to handle results, errors, and completion. This prevents blocking the GUI
        event loop during long-running operations.
        
        Args:
            task: Function to run in background
            *args: Task arguments
            on_result: Callback for successful result (receives result as argument)
            on_error: Callback for errors (receives exception as argument)
            on_finished: Callback when finished (success or error, no arguments)
            **kwargs: Task keyword arguments
            
        Returns:
            QThread instance or None if PyQt6 not available
        
        Example:
            File processing with progress updates::
            
                def process_audio_files(files, output_dir):
                    results = []
                    for file in files:
                        result = convert_file(file, output_dir)
                        results.append(result)
                    return results
                
                def show_results(results):
                    for result in results:
                        file_list.addItem(result)
                    message_box.setText(f"Processed {len(results)} files")
                
                def show_error(error):
                    error_dialog.setText(f"Processing failed: {error}")
                    error_dialog.show()
                
                def cleanup():
                    progress_bar.hide()
                    process_button.setEnabled(True)
                
                # Disable UI during processing
                process_button.setEnabled(False)
                progress_bar.show()
                
                # Run in background
                thread_mgr.run_in_background(
                    process_audio_files,
                    audio_files,
                    output_directory,
                    on_result=show_results,
                    on_error=show_error,
                    on_finished=cleanup
                )
            
            Network request without blocking::
            
                def fetch_version_info(url):
                    import requests
                    response = requests.get(url, timeout=10)
                    return response.json()
                
                thread_mgr.run_in_background(
                    fetch_version_info,
                    'https://api.github.com/repos/owner/repo/releases/latest',
                    on_result=lambda data: update_label.setText(data['tag_name']),
                    on_error=lambda e: logger.warning(f"Version check failed: {e}")
                )
        """
        if not PYQT6_AVAILABLE:
            logger.warning("PyQt6 not available, running task in thread pool")
            future = self._executor.submit(task, *args, **kwargs)
            
            def handle_result():
                try:
                    result = future.result()
                    if on_result:
                        on_result(result)
                except Exception as e:
                    if on_error:
                        on_error(e)
                    else:
                        logger.error(f"Background task error: {e}")
                finally:
                    if on_finished:
                        on_finished()
            
            # Schedule result handling (simplified without Qt)
            threading.Timer(0.1, handle_result).start()
            return None
        
        try:
            # Create worker and thread
            worker = QtWorker(task, *args, **kwargs)
            thread = QThread()
            
            # Move worker to thread
            worker.moveToThread(thread)
            
            # Connect signals
            if on_result:
                worker.signals.result.connect(on_result)
            if on_error:
                worker.signals.error.connect(lambda error_info: on_error(error_info[1]) if on_error else None)
            if on_finished:
                worker.signals.finished.connect(on_finished)
            
            # Connect thread signals
            thread.started.connect(worker.run)
            worker.signals.finished.connect(thread.quit)
            worker.signals.finished.connect(worker.deleteLater)
            thread.finished.connect(thread.deleteLater)
            
            # Track active worker
            with QMutexLocker(self._mutex):
                worker_id = f"worker_{self._worker_counter}"
                self._worker_counter += 1
                self._active_workers[worker_id] = thread
            
            # Cleanup when finished
            def cleanup():
                with QMutexLocker(self._mutex):
                    if worker_id in self._active_workers:
                        del self._active_workers[worker_id]
            
            thread.finished.connect(cleanup)
            
            # Start the thread
            thread.start()
            
            logger.debug(f"Started background task: {worker_id}")
            return thread
            
        except Exception as e:
            logger.error(f"Failed to start background task: {e}")
            if on_error:
                on_error(e)
            return None
    
    def run_in_thread_pool(self, task: Callable, *args, **kwargs) -> Future:
        """
        Run a task in the thread pool executor.
        
        Args:
            task: Function to run
            *args: Task arguments
            **kwargs: Task keyword arguments
            
        Returns:
            Future object for the task
        """
        try:
            future = self._executor.submit(task, *args, **kwargs)
            logger.debug("Submitted task to thread pool")
            return future
        except Exception as e:
            logger.error(f"Failed to submit task to thread pool: {e}")
            raise
    
    def schedule_ui_update(self, update_fn: Callable, delay_ms: int = 0):
        """
        Schedule a UI update to run on the main thread.
        
        Args:
            update_fn: Function to run on main thread
            delay_ms: Delay in milliseconds before running
        """
        if not PYQT6_AVAILABLE:
            logger.warning("PyQt6 not available, running UI update directly")
            if delay_ms > 0:
                threading.Timer(delay_ms / 1000.0, update_fn).start()
            else:
                update_fn()
            return
        
        try:
            if delay_ms > 0:
                QTimer.singleShot(delay_ms, update_fn)
            else:
                # Run immediately on main thread
                QTimer.singleShot(0, update_fn)
                
            logger.debug(f"Scheduled UI update with delay: {delay_ms}ms")
            
        except Exception as e:
            logger.error(f"Failed to schedule UI update: {e}")
            # Fallback: run directly
            update_fn()
    
    def wait_for_workers(self, timeout_ms: int = 5000) -> bool:
        """
        Wait for all active workers to finish.
        
        Args:
            timeout_ms: Timeout in milliseconds
            
        Returns:
            True if all workers finished within timeout
        """
        if not PYQT6_AVAILABLE:
            logger.info("PyQt6 not available, using executor shutdown")
            return True  # Thread pool will handle shutdown
        
        try:
            with QMutexLocker(self._mutex):
                workers_to_wait = list(self._active_workers.values())
            
            for thread in workers_to_wait:
                if thread.isRunning():
                    if not thread.wait(timeout_ms):
                        logger.warning(f"Worker thread did not finish within {timeout_ms}ms")
                        return False
            
            logger.debug("All worker threads finished")
            return True
            
        except Exception as e:
            logger.error(f"Error waiting for workers: {e}")
            return False
    
    def shutdown(self, timeout_s: int = 5):
        """
        Shutdown the thread manager and all workers.
        
        Args:
            timeout_s: Shutdown timeout in seconds
        """
        logger.info("Shutting down Qt thread manager...")
        
        try:
            # Wait for Qt threads to finish
            if PYQT6_AVAILABLE:
                self.wait_for_workers(timeout_s * 1000)
                
                # Force quit any remaining threads
                with QMutexLocker(self._mutex):
                    for thread in self._active_workers.values():
                        if thread.isRunning():
                            thread.quit()
                            if not thread.wait(1000):  # 1 second timeout
                                thread.terminate()
                                thread.wait()
            
            # Shutdown thread pool
            # Note: timeout parameter was added in Python 3.9, use try/except for compatibility
            try:
                self._executor.shutdown(wait=True, timeout=timeout_s)
            except TypeError:
                # Fallback for Python versions < 3.9
                self._executor.shutdown(wait=True)
            
            logger.info("Qt thread manager shutdown completed")
            
        except Exception as e:
            logger.error(f"Error during thread manager shutdown: {e}")
    
    def get_active_worker_count(self) -> int:
        """
        Get the number of active worker threads.
        
        Returns:
            Number of active workers
        """
        if not PYQT6_AVAILABLE:
            return 0  # Can't track without Qt
        
        with QMutexLocker(self._mutex):
            return len([t for t in self._active_workers.values() if t.isRunning()])


# Global thread manager instance
_thread_manager: Optional[QtThreadManager] = None


def get_qt_thread_manager() -> QtThreadManager:
    """
    Get the global Qt thread manager instance.
    
    Returns:
        QtThreadManager singleton instance
    """
    global _thread_manager
    if _thread_manager is None:
        _thread_manager = QtThreadManager()
    return _thread_manager