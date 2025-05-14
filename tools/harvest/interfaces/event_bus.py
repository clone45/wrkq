# harvest/interfaces/event_bus.py

from typing import Callable, Dict, Any, List

class EventBus:
    """Interface for the event publishing/subscription system."""
    
    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to subscribe to
            callback: Function to call when event occurs
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def unsubscribe(self, event_type: str, callback: Callable[..., Any]) -> bool:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event to unsubscribe from
            callback: Function to unsubscribe
            
        Returns:
            True if unsubscription was successful, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")
        
    def publish(self, event_type: str, **data: Any) -> None:
        """
        Publish an event.
        
        Args:
            event_type: Type of event to publish
            **data: Data associated with the event
        """
        raise NotImplementedError("Subclasses must implement this method")