# File: harvest/utils/file_utils.py

import os
import logging
from pathlib import Path
from urllib.parse import urlparse
from datetime import datetime
import re
from typing import Optional, Union

logger = logging.getLogger(__name__)

def _sanitize_filename_part(part: str, max_length: int = 50) -> str:
    """
    Sanitizes a string part to be used in a filename.
    Removes invalid characters and truncates if necessary.
    """
    if not part:
        return "unknown"
    # Remove characters not suitable for filenames
    sanitized = re.sub(r'[\\/*?:"<>|]', "_", part)
    # Replace multiple consecutive underscores or hyphens with a single one
    sanitized = re.sub(r'[_.-]{2,}', '_', sanitized)
    # Truncate
    return sanitized[:max_length].strip('_.-')

def generate_filename_from_url(
    url: str,
    output_directory: Union[str, Path],
    extension: str = "html",
    prefix: Optional[str] = None,
    include_timestamp: bool = True
) -> Path:
    """
    Creates a relatively safe and descriptive filename from a URL,
    placing it within the specified output directory.

    Args:
        url: The URL to base the filename on.
        output_directory: The directory where the file will be saved.
        extension: The file extension (e.g., "html", "json").
        prefix: An optional prefix for the filename.
        include_timestamp: Whether to include a timestamp in the filename.

    Returns:
        A Path object representing the full path to the new file.
    """
    if isinstance(output_directory, str):
        output_dir_path = Path(output_directory)
    else:
        output_dir_path = output_directory

    # Ensure output directory exists
    output_dir_path.mkdir(parents=True, exist_ok=True)

    parsed_url = urlparse(url)
    domain = _sanitize_filename_part(parsed_url.netloc)
    
    # Try to extract a meaningful part from the path or query
    path_part = _sanitize_filename_part(parsed_url.path.strip('/'))
    query_part = _sanitize_filename_part(parsed_url.query)

    # Attempt to get a job ID if present in common LinkedIn URL patterns
    job_id_match = re.search(r'(?:view/|currentJobId=|jobPosting:|jobId=)(\d+)', url)
    meaningful_name_part = ""

    if job_id_match:
        meaningful_name_part = f"job_{job_id_match.group(1)}"
    elif path_part and path_part != "unknown":
        meaningful_name_part = path_part
    elif query_part and query_part != "unknown":
        meaningful_name_part = f"query_{query_part}"
    
    if not meaningful_name_part: # Fallback if no good part found
        meaningful_name_part = "page"


    timestamp_str = f"_{datetime.now().strftime('%Y%m%d_%H%M%S')}" if include_timestamp else ""
    
    filename_parts = []
    if prefix:
        filename_parts.append(_sanitize_filename_part(prefix, 20))
    
    filename_parts.append(domain)
    filename_parts.append(meaningful_name_part) # Use the extracted meaningful part
    
    base_filename = "_".join(filter(None, filename_parts))
    final_filename = f"{base_filename}{timestamp_str}.{extension.lstrip('.')}"
    
    return output_dir_path / final_filename


def save_text_to_file(
    content: str,
    file_path: Union[str, Path],
    encoding: str = "utf-8"
) -> bool:
    """
    Saves text content to a specified file path.

    Args:
        content: The text content to save.
        file_path: The full path (including filename) where the content will be saved.
                   This can be a string or a Path object.
        encoding: The encoding to use for writing the file.

    Returns:
        True if saving was successful, False otherwise.
    """
    try:
        if isinstance(file_path, str):
            path_obj = Path(file_path)
        else:
            path_obj = file_path
            
        # Ensure parent directory exists
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, "w", encoding=encoding) as f:
            f.write(content)
        logger.info(f"Successfully saved content to {path_obj}")
        return True
    except IOError as e:
        logger.error(f"IOError saving content to {file_path}: {e}")
    except Exception as e:
        logger.error(f"Unexpected error saving content to {file_path}: {e}", exc_info=True)
    return False

# Example of adapting your old create_filename (now generate_filename_from_url)
# def old_create_filename(url, output_dir, prefix=None): # From your common utils
#     """Create a filename for the saved HTML based on URL and timestamp."""
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
    
#     domain = urlparse(url).netloc.replace(".", "_")
#     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
#     job_id = extract_job_id_from_url(url) # extract_job_id_from_url would need to be defined or imported
#     if job_id:
#         filename = f"linkedin_job_{job_id}_{timestamp}.html"
#     else:
#         path_parts = urlparse(url).path.strip('/').replace('/', '_')
#         if path_parts:
#             filename = f"{domain}_{path_parts}_{timestamp}.html"
#         else:
#             filename = f"{domain}_{timestamp}.html"
    
#     if prefix:
#         filename = f"{prefix}_{filename}"
    
#     return os.path.join(output_dir, filename)