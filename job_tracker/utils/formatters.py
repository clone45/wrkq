"""
Formatting utility functions
"""

from datetime import datetime
from typing import Any, Union


def format_date(date_value: Any, format_str: str = "%Y-%m-%d") -> str:
    """
    Format a date value as a string
    
    Args:
        date_value: Date value to format (string, datetime, or other)
        format_str: Format string for strftime
        
    Returns:
        Formatted date string or empty string if invalid
    """
    if not date_value:
        return ""
    
    # If already a string, try to parse it
    if isinstance(date_value, str):
        try:
            # Try ISO format first
            dt = datetime.fromisoformat(date_value.replace('Z', '+00:00'))
            return dt.strftime(format_str)
        except ValueError:
            # Return original if parsing fails
            return date_value
    
    # If already a datetime, format it
    if isinstance(date_value, datetime):
        return date_value.strftime(format_str)
    
    # Return string representation for other types
    return str(date_value)


def format_money(value: Union[str, int, float, None]) -> str:
    """
    Format a money value as a string
    
    Args:
        value: Money value to format
        
    Returns:
        Formatted money string or 'Not specified' if invalid
    """
    if value is None:
        return "Not specified"
    
    # If already a string, check for currency symbols
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return "Not specified"
        return value
    
    # Format numbers as currency
    if isinstance(value, (int, float)):
        return f"${value:,.2f}"
    
    return str(value)


def truncate_text(text: str, max_length: int = 50, ellipsis: str = "...") -> str:
    """
    Truncate text to a maximum length
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        ellipsis: Ellipsis string to append
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length-len(ellipsis)] + ellipsis


def clean_html(html: str) -> str:
    """
    Remove HTML tags from a string
    
    Args:
        html: HTML string to clean
        
    Returns:
        Plain text without HTML tags
    """
    if not html:
        return ""
    
    # Simple HTML cleaning - for production use a proper HTML parser
    import re
    clean = re.compile('<.*?>')
    return re.sub(clean, '', html)