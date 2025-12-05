"""
Event Bus Implementation

This module provides a centralized event bus for publishing and subscribing to events.
The event bus allows loose coupling between different parts of the application.
"""

from typing import Any, Callable, Dict, List, Type, Optional
import logging
import weakref
import inspect
from threading import Lock
from .base_events import BaseEvent
from ..utils.logging import get_logger

logger = get_logger(__name__)

# Type alias for event handlers
EventHandler = Callable[[BaseEvent], None]


class EventBus:
    """
    A thread-safe event bus implementation that allows publishing and subscribing to events.
    
    The event bus uses weak references to subscribers to prevent memory leaks
    when subscribers are garbage collected.
    """
    
    def __init__(self):
        """Initialize the event bus."""
        self._subscribers: Dict[Type[BaseEvent], List[weakref.ReferenceType]] = {}
        self._lock = Lock()
        self._name = "EventBus"
    
    def subscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: The function to call when an event of this type is published
        """
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            
            # Use appropriate weak reference type based on handler type
            if inspect.ismethod(handler):
                # For bound methods, use WeakMethod
                weak_handler = weakref.WeakMethod(handler)
            else:
                # For regular functions, use regular weak reference  
                weak_handler = weakref.ref(handler)
            
            self._subscribers[event_type].append(weak_handler)
            
            logger.debug(f"Subscribed handler {handler.__name__} to {event_type.__name__}")
    
    def unsubscribe(self, event_type: Type[BaseEvent], handler: EventHandler) -> None:
        """
        Unsubscribe from events of a specific type.
        
        Args:
            event_type: The type of event to unsubscribe from
            handler: The handler to remove
        """
        with self._lock:
            if event_type not in self._subscribers:
                return
            
            # Remove the handler from the list
            self._subscribers[event_type] = [
                weak_ref for weak_ref in self._subscribers[event_type]
                if weak_ref() is not None and weak_ref() is not handler
            ]
            
            # Clean up empty lists
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
                
            logger.debug(f"Unsubscribed handler {handler.__name__} from {event_type.__name__}")
    
    def publish(self, event: BaseEvent) -> None:
        """
        Publish an event to all subscribers.
        
        Args:
            event: The event to publish
        """
        event_type = type(event)
        
        with self._lock:
            if event_type not in self._subscribers:
                logger.debug(f"No subscribers for event type {event_type.__name__}")
                return
            
            # Get all valid handlers (remove dead weak references)
            valid_handlers = []
            dead_refs = []
            
            for weak_ref in self._subscribers[event_type]:
                handler = weak_ref()
                if handler is not None:
                    valid_handlers.append(handler)
                else:
                    dead_refs.append(weak_ref)
            
            # Clean up dead references
            for dead_ref in dead_refs:
                self._subscribers[event_type].remove(dead_ref)
            
            if not self._subscribers[event_type]:
                del self._subscribers[event_type]
        
        # Call handlers outside of the lock to prevent deadlocks
        logger.trace(f"Publishing {event_type.__name__} to {len(valid_handlers)} subscribers")
        
        for handler in valid_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler {handler.__name__}: {e}", exc_info=True)
    
    def clear_subscribers(self, event_type: Optional[Type[BaseEvent]] = None) -> None:
        """
        Clear subscribers for a specific event type or all event types.
        
        Args:
            event_type: The event type to clear subscribers for. If None, clears all.
        """
        with self._lock:
            if event_type is None:
                self._subscribers.clear()
                logger.debug("Cleared all event subscribers")
            elif event_type in self._subscribers:
                del self._subscribers[event_type]
                logger.debug(f"Cleared subscribers for {event_type.__name__}")
    
    def get_subscriber_count(self, event_type: Type[BaseEvent]) -> int:
        """
        Get the number of active subscribers for an event type.
        
        Args:
            event_type: The event type to count subscribers for
            
        Returns:
            The number of active subscribers
        """
        with self._lock:
            if event_type not in self._subscribers:
                return 0
            
            # Count only valid (non-None) weak references
            valid_count = sum(
                1 for weak_ref in self._subscribers[event_type]
                if weak_ref() is not None
            )
            
            return valid_count


# Global event bus instance
_global_event_bus: Optional[EventBus] = None
_bus_lock = Lock()


def get_event_bus() -> EventBus:
    """
    Get the global event bus instance.
    
    This function ensures there's only one event bus instance
    throughout the application (singleton pattern).
    
    Returns:
        The global EventBus instance
    """
    global _global_event_bus
    
    if _global_event_bus is None:
        with _bus_lock:
            if _global_event_bus is None:
                _global_event_bus = EventBus()
                logger.info("Created global event bus")
    
    return _global_event_bus


def reset_event_bus() -> None:
    """
    Reset the global event bus (primarily for testing purposes).
    
    This clears all subscribers and creates a new event bus instance.
    """
    global _global_event_bus
    
    with _bus_lock:
        if _global_event_bus is not None:
            _global_event_bus.clear_subscribers()
        _global_event_bus = None
        logger.info("Reset global event bus")