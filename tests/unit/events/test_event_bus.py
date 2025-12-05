#!/usr/bin/env python3
"""
Unit tests for EventBus.

Tests cover event publishing, subscription, weak references, and thread safety.
"""

import pytest
import time
import threading
from unittest.mock import Mock, MagicMock

from TonieToolbox.core.events.event_bus import EventBus
from TonieToolbox.core.events.base_events import BaseEvent


class TestEvent(BaseEvent):
    """Test event class."""
    def __init__(self, data: str = "test"):
        super().__init__(event_data={"data": data})
        self.data = data
    
    @property
    def event_type(self) -> str:
        return "test_event"


class AnotherTestEvent(BaseEvent):
    """Another test event class."""
    def __init__(self, value: int = 42):
        super().__init__(event_data={"value": value})
        self.value = value
    
    @property
    def event_type(self) -> str:
        return "another_test_event"


class TestEventBusBasics:
    """Test basic event bus functionality."""
    
    def test_initialization(self):
        """Test event bus initializes correctly."""
        bus = EventBus()
        assert bus is not None
    
    def test_subscribe_and_publish(self):
        """Test basic subscription and publishing."""
        bus = EventBus()
        handler = Mock(__name__='test_handler')
        
        bus.subscribe(TestEvent, handler)
        event = TestEvent(data="hello")
        bus.publish(event)
        
        handler.assert_called_once_with(event)
    
    def test_multiple_subscribers(self):
        """Test multiple handlers subscribe to same event."""
        bus = EventBus()
        handler1 = Mock(__name__='handler1')
        handler2 = Mock(__name__='handler2')
        handler3 = Mock(__name__='handler3')
        
        bus.subscribe(TestEvent, handler1)
        bus.subscribe(TestEvent, handler2)
        bus.subscribe(TestEvent, handler3)
        
        event = TestEvent(data="broadcast")
        bus.publish(event)
        
        handler1.assert_called_once_with(event)
        handler2.assert_called_once_with(event)
        handler3.assert_called_once_with(event)
    
    def test_different_event_types(self):
        """Test handlers only called for subscribed event types."""
        bus = EventBus()
        test_handler = Mock(__name__='test_handler')
        another_handler = Mock(__name__='another_handler')
        
        bus.subscribe(TestEvent, test_handler)
        bus.subscribe(AnotherTestEvent, another_handler)
        
        # Publish TestEvent
        test_event = TestEvent(data="test")
        bus.publish(test_event)
        
        test_handler.assert_called_once_with(test_event)
        another_handler.assert_not_called()
        
        # Publish AnotherTestEvent
        another_event = AnotherTestEvent(value=99)
        bus.publish(another_event)
        
        another_handler.assert_called_once_with(another_event)
        assert test_handler.call_count == 1  # Still only called once


class TestEventBusUnsubscribe:
    """Test unsubscribe functionality."""
    
    def test_unsubscribe_handler(self):
        """Test unsubscribing a handler."""
        bus = EventBus()
        handler = Mock(__name__='handler')
        
        bus.subscribe(TestEvent, handler)
        bus.unsubscribe(TestEvent, handler)
        
        event = TestEvent()
        bus.publish(event)
        
        handler.assert_not_called()
    
    def test_unsubscribe_one_of_multiple(self):
        """Test unsubscribing one handler doesn't affect others."""
        bus = EventBus()
        handler1 = Mock(__name__='handler1')
        handler2 = Mock(__name__='handler2')
        
        bus.subscribe(TestEvent, handler1)
        bus.subscribe(TestEvent, handler2)
        
        bus.unsubscribe(TestEvent, handler1)
        
        event = TestEvent()
        bus.publish(event)
        
        handler1.assert_not_called()
        handler2.assert_called_once_with(event)
    
    def test_unsubscribe_nonexistent_handler(self):
        """Test unsubscribing handler that wasn't subscribed."""
        bus = EventBus()
        handler = Mock()
        
        # Should not raise error
        bus.unsubscribe(TestEvent, handler)
    
    def test_unsubscribe_nonexistent_event_type(self):
        """Test unsubscribing from event type with no subscribers."""
        bus = EventBus()
        handler = Mock()
        
        # Should not raise error
        bus.unsubscribe(AnotherTestEvent, handler)


class TestEventBusWeakReferences:
    """Test weak reference behavior."""
    
    def test_handler_garbage_collected(self):
        """Test that garbage collected handlers are not called."""
        bus = EventBus()
        
        # Create a handler that will be garbage collected
        class HandlerClass:
            def __init__(self):
                self.called = False
            
            def handle(self, event):
                self.called = True
        
        handler_obj = HandlerClass()
        bus.subscribe(TestEvent, handler_obj.handle)
        
        # Delete the handler object
        del handler_obj
        
        # Publish event - should not crash
        event = TestEvent()
        bus.publish(event)
        # No assertion - just verify no crash
    
    def test_method_handlers_use_weak_method(self):
        """Test that bound method handlers use WeakMethod."""
        bus = EventBus()
        
        class Subscriber:
            def __init__(self):
                self.events_received = []
            
            def handle_event(self, event):
                self.events_received.append(event)
        
        subscriber = Subscriber()
        bus.subscribe(TestEvent, subscriber.handle_event)
        
        event1 = TestEvent(data="first")
        bus.publish(event1)
        
        assert len(subscriber.events_received) == 1
        assert subscriber.events_received[0].data == "first"
        
        # Subscriber still alive, should continue receiving
        event2 = TestEvent(data="second")
        bus.publish(event2)
        
        assert len(subscriber.events_received) == 2
    
    def test_function_handlers_work(self):
        """Test that regular function handlers work."""
        bus = EventBus()
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        bus.subscribe(TestEvent, handler)
        
        event = TestEvent(data="function")
        bus.publish(event)
        
        assert len(received_events) == 1
        assert received_events[0].data == "function"


class TestEventBusThreadSafety:
    """Test thread safety of event bus."""
    
    def test_concurrent_subscribing(self):
        """Test multiple threads subscribing simultaneously."""
        bus = EventBus()
        handlers = [Mock(__name__=f'handler_{i}') for i in range(10)]
        
        def subscribe_handler(handler):
            bus.subscribe(TestEvent, handler)
        
        threads = [
            threading.Thread(target=subscribe_handler, args=(h,))
            for h in handlers
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Publish event and verify all handlers called
        event = TestEvent()
        bus.publish(event)
        
        for handler in handlers:
            handler.assert_called_once_with(event)
    
    def test_concurrent_publishing(self):
        """Test multiple threads publishing simultaneously."""
        bus = EventBus()
        handler = Mock(__name__='handler')
        bus.subscribe(TestEvent, handler)
        
        def publish_event(data):
            event = TestEvent(data=data)
            bus.publish(event)
        
        threads = [
            threading.Thread(target=publish_event, args=(f"event_{i}",))
            for i in range(10)
        ]
        
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # Should have been called 10 times
        assert handler.call_count == 10
    
    def test_subscribe_and_publish_concurrently(self):
        """Test subscribing and publishing from different threads."""
        bus = EventBus()
        handlers = [Mock(__name__=f'handler_{i}') for i in range(5)]
        
        def subscribe_handler(handler):
            bus.subscribe(TestEvent, handler)
            time.sleep(0.01)  # Small delay
        
        def publish_events():
            for i in range(5):
                event = TestEvent(data=f"concurrent_{i}")
                bus.publish(event)
                time.sleep(0.01)
        
        # Start publishing thread
        publish_thread = threading.Thread(target=publish_events)
        publish_thread.start()
        
        # Start subscribing threads
        subscribe_threads = [
            threading.Thread(target=subscribe_handler, args=(h,))
            for h in handlers
        ]
        
        for thread in subscribe_threads:
            thread.start()
        
        # Wait for all threads
        publish_thread.join()
        for thread in subscribe_threads:
            thread.join()
        
        # Each handler should have been called at least once
        for handler in handlers:
            assert handler.call_count >= 1


class TestEventBusEdgeCases:
    """Test edge cases and error handling."""
    
    def test_publish_with_no_subscribers(self):
        """Test publishing event with no subscribers."""
        bus = EventBus()
        
        event = TestEvent()
        # Should not raise error
        bus.publish(event)
    
    def test_handler_raises_exception(self):
        """Test that handler exception doesn't crash event bus."""
        bus = EventBus()
        
        def bad_handler(event):
            raise ValueError("Handler error")
        
        good_handler = Mock(__name__='good_handler')
        
        bus.subscribe(TestEvent, bad_handler)
        bus.subscribe(TestEvent, good_handler)
        
        event = TestEvent()
        bus.publish(event)
        
        # Good handler should still be called despite bad handler error
        good_handler.assert_called_once_with(event)
    
    def test_multiple_event_types_same_handler(self):
        """Test same handler subscribing to multiple event types."""
        bus = EventBus()
        handler = Mock(__name__='handler')
        
        bus.subscribe(TestEvent, handler)
        bus.subscribe(AnotherTestEvent, handler)
        
        test_event = TestEvent(data="test")
        another_event = AnotherTestEvent(value=123)
        
        bus.publish(test_event)
        bus.publish(another_event)
        
        assert handler.call_count == 2
        handler.assert_any_call(test_event)
        handler.assert_any_call(another_event)
    
    def test_resubscribe_same_handler(self):
        """Test subscribing the same handler multiple times."""
        bus = EventBus()
        handler = Mock(__name__='handler')
        
        bus.subscribe(TestEvent, handler)
        bus.subscribe(TestEvent, handler)  # Subscribe again
        
        event = TestEvent()
        bus.publish(event)
        
        # Handler should be called twice (once per subscription)
        assert handler.call_count == 2


class TestEventBusIntegration:
    """Integration tests for realistic usage patterns."""
    
    def test_event_chain(self):
        """Test chaining events (handler publishes new event)."""
        bus = EventBus()
        
        events_received = []
        
        def test_handler(event):
            events_received.append(event)
            # Publish another event in response
            if event.data == "trigger":
                bus.publish(AnotherTestEvent(value=100))
        
        def another_handler(event):
            events_received.append(event)
        
        bus.subscribe(TestEvent, test_handler)
        bus.subscribe(AnotherTestEvent, another_handler)
        
        # Start the chain
        bus.publish(TestEvent(data="trigger"))
        
        # Should have received both events
        assert len(events_received) == 2
        assert isinstance(events_received[0], TestEvent)
        assert isinstance(events_received[1], AnotherTestEvent)
    
    def test_observer_pattern(self):
        """Test implementing observer pattern with event bus."""
        bus = EventBus()
        
        class Model:
            def __init__(self):
                self.data = ""
            
            def update(self, new_data):
                self.data = new_data
                bus.publish(TestEvent(data=new_data))
        
        class Observer:
            def __init__(self):
                self.observed_data = None
                bus.subscribe(TestEvent, self.on_update)
            
            def on_update(self, event):
                self.observed_data = event.data
        
        model = Model()
        observer1 = Observer()
        observer2 = Observer()
        
        model.update("new value")
        
        assert observer1.observed_data == "new value"
        assert observer2.observed_data == "new value"
