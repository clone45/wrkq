import os
import traceback
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class LogLevel(Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class Slogger:
    log_path = "logs/wrkq.log"
    
    @classmethod
    def _ensure_log_directory(cls):
        """Ensure that the logs directory exists."""
        log_dir = os.path.dirname(cls.log_path)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
    
    @classmethod
    def log(cls, message: str, level: LogLevel = LogLevel.INFO, context: Optional[Dict[str, Any]] = None):
        """
        Log a message with an optional level and context.
        
        Args:
            message: The message to log
            level: The log level (DEBUG, INFO, WARNING, ERROR)
            context: Optional dictionary of contextual information
        """
        cls._ensure_log_directory()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Format the log message
        log_message = f"{timestamp} - {level.value} - {message}"
        
        # Add context if provided
        if context:
            context_str = " | ".join([f"{k}={v}" for k, v in context.items()])
            log_message += f" | {context_str}"
            
        log_message += "\n"

        with open(cls.log_path, "a", encoding="utf-8") as f:
            f.write(log_message)
            
    @classmethod
    def debug(cls, message: str, context: Optional[Dict[str, Any]] = None):
        """Log a debug message."""
        cls.log(message, LogLevel.DEBUG, context)
    
    @classmethod
    def info(cls, message: str, context: Optional[Dict[str, Any]] = None):
        """Log an info message."""
        cls.log(message, LogLevel.INFO, context)
    
    @classmethod
    def warning(cls, message: str, context: Optional[Dict[str, Any]] = None):
        """Log a warning message."""
        cls.log(message, LogLevel.WARNING, context)
    
    @classmethod
    def error(cls, message: str, context: Optional[Dict[str, Any]] = None):
        """Log an error message."""
        cls.log(message, LogLevel.ERROR, context)
    
    @classmethod
    def exception(cls, e: Exception, message: str = "Exception occurred", context: Optional[Dict[str, Any]] = None):
        """
        Log an exception with traceback.
        
        Args:
            e: The exception to log
            message: An optional message describing the context of the exception
            context: Optional dictionary of contextual information
        """
        exc_type = type(e).__name__
        exc_message = str(e)
        exc_traceback = traceback.format_exc()
        
        error_context = context or {}
        error_context.update({
            "exception_type": exc_type,
            "exception_message": exc_message
        })
        
        # Log the main error message
        cls.error(f"{message}: {exc_type} - {exc_message}", error_context)
        
        # Log the traceback separately for readability
        cls._ensure_log_directory()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(cls.log_path, "a", encoding="utf-8") as f:
            f.write(f"{timestamp} - {LogLevel.ERROR.value} - TRACEBACK:\n{exc_traceback}\n")