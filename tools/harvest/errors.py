# harvest/errors.py

class HarvestError(Exception):
    """Base class for all harvester errors."""
    pass
    
class NetworkError(HarvestError):
    """Error related to network operations."""
    pass
    
class AuthenticationError(NetworkError):
    """Error related to authentication."""
    pass
    
class ParseError(HarvestError):
    """Error related to parsing responses."""
    pass
    
class ConfigError(HarvestError):
    """Error related to configuration."""
    pass
    
class DatabaseError(HarvestError):
    """Error related to database operations."""
    pass