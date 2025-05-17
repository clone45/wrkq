# harvest/interfaces/event_bus.py

from typing import Callable, Dict, Any, List, Set
from ..events import EventType

class EventBus:
    """Interface for the event publishing/subscription system."""
    
    def subscribe(self, event_type: EventType, callback: Callable[..., Any]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to (EventType enum)
            callback: Function to call when event occurs
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def unsubscribe(self, event_type: EventType, callback: Callable[..., Any]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from (EventType enum)
            callback: Function to unsubscribe
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def publish(self, event_type: EventType, **data: Any) -> None:
        """
        Publish an event.
        
        Args:
            event_type: Type of event to publish (EventType enum)
            **data: Data associated with the event
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_event_types(self) -> Set[EventType]:
        """
        Get all event types that have subscribers.
        
        Returns:
            Set of event types with active subscribers
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def get_subscriber_count(self, event_type: EventType) -> int:
        """
        Get the number of subscribers for an event type.
        
        Args:
            event_type: The event type to check (EventType enum)
            
        Returns:
            Number of subscribers for the event type
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def has_subscribers(self, event_type: EventType) -> bool:
        """
        Check if an event type has any subscribers.
        
        Args:
            event_type: The event type to check (EventType enum)
            
        Returns:
            True if the event type has subscribers, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def clear_all_subscriptions(self) -> None:
        """
        Clear all event subscriptions.
        Useful for testing or when shutting down the application.
        """
        raise NotImplementedError("Subclasses must implement this method")