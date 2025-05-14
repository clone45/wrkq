# harvest/core/event_bus.py

import logging
from typing import Callable, Dict, Any, List, Set
from ..interfaces.event_bus import EventBus as EventBusInterface

logger = logging.getLogger(__name__)

class EventBus(EventBusInterface):
    """
    Implementation of the event bus for publishing and subscribing to events.
    
    The event bus allows components to communicate without direct dependencies,
    enabling loose coupling between system parts.
    """
    
    def __init__(self, debug_logging: bool = False):
        """
        Initialize a new event bus.
        
        Args:
            debug_logging: Whether to log all events for debugging
        """
        self.listeners: Dict[str, List[Callable[..., Any]]] = {}
        self.debug_logging = debug_logging
        
    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        if event_type not in self.listeners:
            self.listeners[event_type] = []
            
        # Avoid duplicate subscriptions
        if callback not in self.listeners[event_type]:
            self.listeners[event_type].append(callback)
            logger.debug(f"Subscribed to event '{event_type}'")
        
    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to unsubscribe
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        if event_type in self.listeners and callback in self.listeners[event_type]:
            self.listeners[event_type].remove(callback)
            logger.debug(f"Unsubscribed from event '{event_type}'")
            return True
        return False
        
    def publish(self, event_type: str, **data: Any) -> None:
        """
        Publish an event.
        
        Args:
            event_type: Type of event to publish
            **data: Data associated with the event
        """
        if self.debug_logging:
            logger.debug(f"Event published: {event_type} - {data}")
            
        # Add the event_type to the data for callbacks that want it
        event_data = {"event_type": event_type, **data}
        
        if event_type in self.listeners:
            for callback in self.listeners[event_type]:
                try:
                    callback(**event_data)
                except Exception as e:
                    # Don't let callback errors disrupt the event bus
                    logger.error(f"Error in event handler for '{event_type}': {e}")
    
    def get_event_types(self) -> Set[str]:
        """
        Get all event types that have subscribers.
        
        Returns:
            Set of event types with active subscribers
        """
        return set(self.listeners.keys())
    
    def get_subscriber_count(self, event_type: str) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to check
            
        Returns:
            Number of subscribers for the event type
        """
        return len(self.listeners.get(event_type, []))
        
    def has_subscribers(self, event_type: str) -> bool:
        """
        Check if an event type has any subscribers.
        
        Args:
            event_type: The event type to check
            
        Returns:
            True if the event type has subscribers, False otherwise
        """
        return event_type in self.listeners and len(self.listeners[event_type]) > 0
        
    def clear_all_subscriptions(self) -> None:
        """
        Clear all event subscriptions.
        Useful for testing or when shutting down the application.
        """
        self.listeners.clear()
        logger.debug("All event subscriptions cleared")