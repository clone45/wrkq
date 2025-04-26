# job_tracker/db/connection.py

"""
MongoDB connection handler
"""

from pymongo import MongoClient


class MongoDBConnection:
    """
    Handles basic connection to MongoDB
    """
    
    def __init__(self, config):
        """
        Initialize MongoDB connection
        
        Args:
            config: Configuration dictionary containing MongoDB settings
        """
        self.client = MongoClient(config["mongodb"]["uri"])
        self.db = self.client.get_database(config["mongodb"]["database"])
        
    def col(self, name: str):
        """
        Get a collection by name
        
        Args:
            name: Collection name
            
        Returns:
            MongoDB collection
        """
        return self.db[name]