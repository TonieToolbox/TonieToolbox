#!/usr/bin/env python3
"""
Unit tests for parallel executor.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from concurrent.futures import Future

from TonieToolbox.core.processing.infrastructure.parallel_executor import (
    ParallelExecutor,
    ThreadPoolParallelExecutor,
    QtParallelExecutor,
    create_parallel_executor
)


class TestThreadPoolParallelExecutor:
    """Test ThreadPoolExecutor-based parallel executor."""
    
    def test_initialization(self):
        """Test executor initialization."""
        executor = ThreadPoolParallelExecutor(max_workers=4)
        
        assert executor.max_workers == 4
        assert executor._executor is not None
    
    def test_execute_batch_with_empty_list(self):
        """Test batch execution with empty item list."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        def task(item):
            return {'status': 'completed', 'item': item}
        
        results = executor.execute_batch(task, [])
        
        assert results == []
        executor.shutdown()
    
    def test_execute_batch_successful(self):
        """Test successful batch execution."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        def task(item):
            return {'status': 'completed', 'item': item, 'value': item * 2}
        
        items = [1, 2, 3, 4]
        results = executor.execute_batch(task, items)
        
        assert len(results) == 4
        assert all(r['status'] == 'completed' for r in results)
        assert sum(r['value'] for r in results) == 20  # (1*2 + 2*2 + 3*2 + 4*2)
        
        executor.shutdown()
    
    def test_execute_batch_with_progress_callback(self):
        """Test batch execution with progress tracking."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        progress_calls = []
        
        def task(item):
            return {'status': 'completed', 'item': item}
        
        def on_progress(completed, total):
            progress_calls.append((completed, total))
        
        items = [1, 2, 3]
        results = executor.execute_batch(task, items, on_progress=on_progress)
        
        assert len(results) == 3
        assert len(progress_calls) == 3
        assert progress_calls[-1] == (3, 3)  # Final progress
        
        executor.shutdown()
    
    def test_execute_batch_with_completion_callback(self):
        """Test batch execution with item completion callback."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        completed_items = []
        
        def task(item):
            return {'status': 'completed', 'item': item}
        
        def on_complete(result):
            completed_items.append(result)
        
        items = [1, 2, 3]
        results = executor.execute_batch(task, items, on_item_complete=on_complete)
        
        assert len(results) == 3
        assert len(completed_items) == 3
        
        executor.shutdown()
    
    def test_execute_batch_with_errors_continue(self):
        """Test batch execution with errors (continue_on_error=True)."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        def task(item):
            if item == 2:
                raise ValueError(f"Error processing {item}")
            return {'status': 'completed', 'item': item}
        
        items = [1, 2, 3]
        results = executor.execute_batch(task, items, continue_on_error=True)
        
        assert len(results) == 3
        completed = [r for r in results if r['status'] == 'completed']
        failed = [r for r in results if r['status'] == 'failed']
        
        assert len(completed) == 2
        assert len(failed) == 1
        assert 'error' in failed[0]
        
        executor.shutdown()
    
    def test_execute_batch_with_errors_stop(self):
        """Test batch execution with errors (continue_on_error=False)."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        def task(item):
            if item == 2:
                raise ValueError(f"Error processing {item}")
            return {'status': 'completed', 'item': item}
        
        items = [1, 2, 3, 4]
        results = executor.execute_batch(task, items, continue_on_error=False)
        
        # Should have processed some items before error
        assert len(results) >= 1  # At least one result
        failed = [r for r in results if r['status'] == 'failed']
        assert len(failed) >= 1  # At least one failed
        
        executor.shutdown()
    
    def test_shutdown(self):
        """Test executor shutdown."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        # Execute a task
        def task(item):
            return {'status': 'completed'}
        
        executor.execute_batch(task, [1])
        
        # Shutdown should not raise
        executor.shutdown()
        executor.shutdown(timeout=1)  # Multiple shutdowns should be safe


class TestQtParallelExecutor:
    """Test Qt-based parallel executor."""
    
    def test_initialization(self):
        """Test Qt executor initialization."""
        mock_thread_manager = Mock()
        executor = QtParallelExecutor(mock_thread_manager, max_workers=4)
        
        assert executor.max_workers == 4
        assert executor.thread_manager == mock_thread_manager
    
    def test_execute_batch_with_qt_thread_manager(self):
        """Test batch execution with Qt thread manager."""
        mock_thread_manager = Mock()
        
        # Mock run_in_thread_pool to return futures
        def create_future(task, item):
            future = Future()
            future.set_result(task(item))
            return future
        
        mock_thread_manager.run_in_thread_pool.side_effect = create_future
        mock_thread_manager.schedule_ui_update = Mock(side_effect=lambda fn, delay_ms=0: fn())
        
        executor = QtParallelExecutor(mock_thread_manager, max_workers=2)
        
        def task(item):
            return {'status': 'completed', 'item': item}
        
        items = [1, 2, 3]
        results = executor.execute_batch(task, items)
        
        assert len(results) == 3
        assert all(r['status'] == 'completed' for r in results)
        assert mock_thread_manager.run_in_thread_pool.call_count == 3
    
    def test_qt_executor_schedules_ui_updates(self):
        """Test that Qt executor schedules UI updates on main thread."""
        mock_thread_manager = Mock()
        ui_updates = []
        
        # Mock run_in_thread_pool
        def create_future(task, item):
            future = Future()
            future.set_result(task(item))
            return future
        
        mock_thread_manager.run_in_thread_pool.side_effect = create_future
        
        # Track UI updates
        def track_update(fn, delay_ms=0):
            ui_updates.append(('schedule', delay_ms))
            fn()  # Execute the update
        
        mock_thread_manager.schedule_ui_update.side_effect = track_update
        
        executor = QtParallelExecutor(mock_thread_manager, max_workers=2)
        
        progress_calls = []
        
        def task(item):
            return {'status': 'completed', 'item': item}
        
        def on_progress(completed, total):
            progress_calls.append((completed, total))
        
        items = [1, 2]
        executor.execute_batch(task, items, on_progress=on_progress)
        
        # Should have scheduled UI updates for progress
        assert len(ui_updates) >= 2
        assert len(progress_calls) == 2
    
    def test_qt_executor_shutdown_is_noop(self):
        """Test that Qt executor shutdown is a no-op."""
        mock_thread_manager = Mock()
        executor = QtParallelExecutor(mock_thread_manager, max_workers=2)
        
        # Shutdown should not raise and not call thread manager
        executor.shutdown()
        
        mock_thread_manager.shutdown.assert_not_called()


class TestParallelExecutorFactory:
    """Test parallel executor factory function."""
    
    def test_create_thread_pool_executor(self):
        """Test creating thread pool executor (no Qt manager)."""
        executor = create_parallel_executor(max_workers=4)
        
        assert isinstance(executor, ThreadPoolParallelExecutor)
        assert executor.max_workers == 4
        
        executor.shutdown()
    
    def test_create_qt_executor(self):
        """Test creating Qt executor (with Qt manager)."""
        mock_qt_manager = Mock()
        executor = create_parallel_executor(max_workers=4, qt_thread_manager=mock_qt_manager)
        
        assert isinstance(executor, QtParallelExecutor)
        assert executor.max_workers == 4
        assert executor.thread_manager == mock_qt_manager
    
    def test_factory_defaults(self):
        """Test factory function with default parameters."""
        executor = create_parallel_executor()
        
        assert isinstance(executor, ThreadPoolParallelExecutor)
        assert executor.max_workers == 4
        
        executor.shutdown()


class TestParallelExecutorIntegration:
    """Integration tests for parallel executor."""
    
    def test_parallel_folder_processing_simulation(self):
        """Simulate parallel folder processing workflow."""
        executor = ThreadPoolParallelExecutor(max_workers=3)
        
        # Simulate folder processing
        folders = [
            {'name': 'Folder1', 'path': '/music/folder1', 'file_count': 5},
            {'name': 'Folder2', 'path': '/music/folder2', 'file_count': 3},
            {'name': 'Folder3', 'path': '/music/folder3', 'file_count': 8},
        ]
        
        def process_folder(folder_info):
            # Simulate processing
            import time
            time.sleep(0.01)  # Simulate work
            
            return {
                'status': 'completed',
                'folder_name': folder_info['name'],
                'input_path': folder_info['path'],
                'output_path': f"/output/{folder_info['name']}.taf",
                'file_count': folder_info['file_count']
            }
        
        progress_updates = []
        
        def track_progress(completed, total):
            progress_updates.append(completed / total)
        
        results = executor.execute_batch(
            process_folder,
            folders,
            on_progress=track_progress,
            continue_on_error=True
        )
        
        assert len(results) == 3
        assert all(r['status'] == 'completed' for r in results)
        assert len(progress_updates) == 3
        assert progress_updates[-1] == 1.0  # 100% complete
        
        # Verify all folders processed
        processed_names = {r['folder_name'] for r in results}
        assert processed_names == {'Folder1', 'Folder2', 'Folder3'}
        
        executor.shutdown()
    
    def test_error_handling_in_batch(self):
        """Test error handling during batch processing."""
        executor = ThreadPoolParallelExecutor(max_workers=2)
        
        def flaky_task(item):
            if item % 2 == 0:
                raise RuntimeError(f"Failed on {item}")
            return {'status': 'completed', 'item': item}
        
        items = [1, 2, 3, 4, 5]
        results = executor.execute_batch(flaky_task, items, continue_on_error=True)
        
        assert len(results) == 5
        
        successful = [r for r in results if r['status'] == 'completed']
        failed = [r for r in results if r['status'] == 'failed']
        
        assert len(successful) == 3  # 1, 3, 5
        assert len(failed) == 2  # 2, 4
        
        executor.shutdown()
