# File: harvest/utils/http_utils.py

import time
import random
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Any

from curl_cffi import requests # Assuming curl_cffi is a direct dependency now

from ..errors import NetworkError, AuthenticationError # Import your custom errors

logger = logging.getLogger(__name__)

# --- Constants (can be overridden by parameters or config later) ---
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY_SECONDS = 5
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_IMPERSONATE_BROWSER = "chrome110" # From your old fetch.py

# --- Helper Functions (adapted from your old common/utils.py) ---

def get_random_user_agent() -> str:
    """Return a random user agent string."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
    ]
    return random.choice(user_agents)

def load_cookies_from_json_file(cookie_file_path: Optional[Path]) -> Dict[str, str]:
    """
    Load cookies from a JSON file (Netscape format or array of dicts).
    Converts to a dictionary format expected by requests.
    """
    if not cookie_file_path or not cookie_file_path.exists():
        logger.debug(f"Cookie file not provided or not found at: {cookie_file_path}")
        return {}

    try:
        with open(cookie_file_path, 'r', encoding='utf-8') as f:
            cookies_data = json.load(f)
            
        cookies_dict: Dict[str, str] = {}
        if isinstance(cookies_data, list): # Common format (e.g., from browser extensions)
            for cookie_item in cookies_data:
                if isinstance(cookie_item, dict) and 'name' in cookie_item and 'value' in cookie_item:
                    cookies_dict[cookie_item['name']] = cookie_item['value']
        elif isinstance(cookies_data, dict): # If already in dict format
            cookies_dict = cookies_data
        else:
            logger.warning(f"Unexpected cookie file format in {cookie_file_path}. Expected list or dict.")
            return {}
            
        logger.info(f"Loaded {len(cookies_dict)} cookies from {cookie_file_path}")
        return cookies_dict
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from cookie file {cookie_file_path}: {e}")
        return {}
    except Exception as e:
        logger.error(f"Error loading cookies from {cookie_file_path}: {e}")
        return {}

def _prepare_default_headers() -> Dict[str, str]:
    """Prepares a dictionary of default headers to mimic a browser."""
    headers = {
        "User-Agent": get_random_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br", # curl_cffi handles encoding
        "DNT": "1", # Do Not Track
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none", # For initial requests
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    # Add Referer sometimes
    if random.random() > 0.5:
        popular_sites = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.linkedin.com/feed/", # More relevant referer
            "https://www.linkedin.com/",
        ]
        headers["Referer"] = random.choice(popular_sites)
    return headers

# --- Main Fetching Function (adapted from your old fetch.py) ---

def fetch_page_content(
    url: str,
    cookie_file: Optional[str | Path] = None, # Accept str or Path
    max_retries: int = DEFAULT_MAX_RETRIES,
    retry_delay: int = DEFAULT_RETRY_DELAY_SECONDS,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
    custom_headers: Optional[Dict[str, str]] = None,
    impersonate: str = DEFAULT_IMPERSONATE_BROWSER,
    proxies: Optional[Dict[str, str]] = None,
    verbose_logging: bool = True # Controls detailed logging within this function
) -> Optional[requests.Response]:
    """
    Fetch a web page using curl_cffi with measures to avoid being blocked.
    Uses authentication cookies if provided.

    Args:
        url: URL to fetch.
        cookie_file: Path to cookie file (JSON format).
        max_retries: Maximum number of retries on failure.
        retry_delay: Base delay between retries (will be randomized).
        timeout: Request timeout in seconds.
        custom_headers: Optional dictionary of custom headers to merge with defaults.
        impersonate: Browser profile to impersonate (e.g., "chrome110").
        proxies: Optional dictionary of proxies.
        verbose_logging: If True, logs detailed information about the fetch attempt.

    Returns:
        requests.Response object on success, None on failure after all retries.
        
    Raises:
        NetworkError: For persistent network issues after retries.
        AuthenticationError: If an authentication-related issue is detected.
    """
    if cookie_file and isinstance(cookie_file, str):
        cookie_file_path = Path(cookie_file)
    elif isinstance(cookie_file, Path):
        cookie_file_path = cookie_file
    else:
        cookie_file_path = None

    loaded_cookies = load_cookies_from_json_file(cookie_file_path)
    
    current_retry = 0
    while current_retry <= max_retries:
        try:
            if current_retry > 0:
                jitter = random.uniform(0.8, 1.2) # Slightly different jitter
                sleep_time = retry_delay * (2 ** (current_retry -1)) * jitter # Exponential backoff with jitter
                sleep_time = min(sleep_time, 60) # Cap sleep time
                if verbose_logging:
                    logger.info(f"Waiting {sleep_time:.2f} seconds before retry {current_retry}/{max_retries} for {url}")
                time.sleep(sleep_time)

            # Prepare headers
            headers = _prepare_default_headers()
            if custom_headers:
                headers.update(custom_headers) # Merge custom headers, custom ones take precedence

            if verbose_logging:
                logger.info(f"Fetching {url} (Attempt {current_retry + 1}/{max_retries + 1})")
                if loaded_cookies:
                    logger.info(f"Using {len(loaded_cookies)} cookies from file.")
            
            response = requests.get(
                url,
                headers=headers,
                impersonate=impersonate,
                timeout=timeout,
                proxies=proxies,
                allow_redirects=True,
                cookies=loaded_cookies,
            )

            # Check for successful status codes
            if response.status_code == 200:
                # Further check if it's a login page despite 200 OK with cookies
                if loaded_cookies and ("Sign In" in response.text or "checkpoint/lg/login" in response.url):
                    logger.warning(
                        f"Status 200 for {url}, but content suggests a login page. "
                        "Cookie authentication might have failed or cookies expired."
                    )
                    # This could be treated as a form of AuthenticationError if it persists
                    if current_retry == max_retries: # If this happens on the last retry
                        raise AuthenticationError(f"Authentication failed for {url}: redirected to login despite cookies.")
                    # Otherwise, let it retry
                else:
                    if verbose_logging:
                        logger.info(f"Successfully fetched {url}. Status: {response.status_code}. Length: {len(response.content)} bytes.")
                    return response # Success
            
            # Handle specific error codes
            elif response.status_code in [401, 403]:
                logger.error(f"Authentication/Authorization error for {url}. Status: {response.status_code}.")
                # This is a clear authentication issue, probably no point in retrying with same cookies
                raise AuthenticationError(f"Failed for {url} with status {response.status_code}. Check cookies/permissions.")
            elif response.status_code == 429:
                logger.warning(f"Rate limited (429 Too Many Requests) for {url}. Retrying might help.")
                # Retry will happen due to loop structure
            else:
                logger.warning(f"Failed to fetch {url}. Status: {response.status_code}. Content preview: {response.text[:200]}")
                # Retry for other client/server errors

        except requests.RequestsError as e: # Catch specific curl_cffi errors
            logger.warning(f"Request failed for {url} (Attempt {current_retry + 1}): {e}")
            if current_retry == max_retries: # If this was the last retry
                raise NetworkError(f"Persistent request failure for {url} after {max_retries+1} attempts: {e}") from e
        except AuthenticationError: # Re-raise AuthenticationError to stop retries for it
            raise
        except Exception as e: # Catch other unexpected errors during the request process
            logger.error(f"Unexpected error during fetch attempt {current_retry + 1} for {url}: {e}", exc_info=True)
            if current_retry == max_retries:
                raise NetworkError(f"Unexpected error on final attempt for {url}: {e}") from e
        
        current_retry += 1

    logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts.")
    # If loop finishes without returning/raising, it means all retries failed for non-auth HTTP errors
    raise NetworkError(f"All retries failed for {url}. Last status might have been non-200 or a request exception occurred.")