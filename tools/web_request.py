"""Web content fetching tool"""

import httpx
import re
from typing import Union, Dict, Any
from tools.registry import ToolRegistry

# Global session store for maintaining state across requests
_session_store: Dict[str, httpx.Client] = {}

# Global CSRF token store per session
_csrf_store: Dict[str, Dict[str, str]] = {}


def get_or_create_session(session_id: str = "default") -> httpx.Client:
    """Get or create a persistent session for maintaining cookies/state"""
    if session_id not in _session_store:
        _session_store[session_id] = httpx.Client(
            timeout=3.0,  # 3 second timeout
            follow_redirects=True,
            headers={'User-Agent': 'RedTeamAgent/1.0'}
        )
    return _session_store[session_id]


def get_stored_csrf(session_id: str) -> Dict[str, str]:
    """Get stored CSRF tokens for a session"""
    return _csrf_store.get(session_id, {})


def store_csrf(session_id: str, tokens: Dict[str, str]):
    """Store CSRF tokens for a session"""
    if session_id not in _csrf_store:
        _csrf_store[session_id] = {}
    _csrf_store[session_id].update(tokens)


def clear_session(session_id: str = "default"):
    """Clear a session"""
    if session_id in _session_store:
        _session_store[session_id].close()
        del _session_store[session_id]
    if session_id in _csrf_store:
        del _csrf_store[session_id]


def setup_web_tools(registry: ToolRegistry):
    """Register web fetching tools"""
    
    @registry.register(
        name="web_request",
        description="Fetch content from a URL using HTTP GET or POST. Session cookies are automatically managed - never pass cookies as a parameter. CSRF tokens are automatically detected, stored, and injected into POST requests.",
        parameters={
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch (must start with http:// or https://)"
                },
                "method": {
                    "type": "string",
                    "enum": ["GET", "POST"],
                    "description": "HTTP method to use",
                    "default": "GET"
                },
                "headers": {
                    "type": "object",
                    "description": "Optional HTTP headers as key-value pairs. Do NOT include Cookie header - cookies are managed automatically.",
                    "default": {}
                },
                "data": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object"}
                    ],
                    "description": "Data to send in POST request (use this parameter, not 'body'). Can be a dict for form data or a string. CSRF tokens will be automatically added if available."
                },
                "body": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object"}
                    ],
                    "description": "Alias for 'data' parameter. Use 'data' instead for consistency."
                },
                "content_type": {
                    "type": "string",
                    "enum": ["form", "json", "raw"],
                    "description": "How to send the data: 'form' for form-encoded, 'json' for JSON, 'raw' for raw string",
                    "default": "form"
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID to maintain cookies/state and CSRF tokens. Use the same session_id for related requests.",
                    "default": "default"
                }
            },
            "required": ["url"]
        }
    )
    def web_request(
        url: str,
        method: str = "GET",
        headers: dict = None,
        data: Union[str, dict] = "",
        content_type: str = "form",
        session_id: str = "default",
        body: Union[str, dict] = None  # Alias for data (common naming)
    ) -> str:
        """Fetch web content"""
        try:
            # Handle 'body' parameter as alias for 'data'
            if body is not None:
                data = body
            
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                return "Error: URL must start with http:// or https://"
            
            # Set default headers
            if headers is None:
                headers = {}
            
            # Remove Cookie header if manually set - session management is automatic
            if 'Cookie' in headers:
                del headers['Cookie']
            if 'cookie' in headers:
                del headers['cookie']
            
            # Add user agent if not provided
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'RedTeamAgent/1.0'
            
            # Prepare data based on content type
            request_data = None
            request_json = None
            
            # Handle different data input types
            if isinstance(data, dict):
                # Dict input - auto-inject CSRF tokens for POST requests with form data
                if method.upper() == "POST" and content_type == "form":
                    stored_csrf = get_stored_csrf(session_id)
                    # Inject stored CSRF tokens if not already present in data
                    for token_name, token_value in stored_csrf.items():
                        if token_name not in data:
                            data[token_name] = token_value
                
                # Process data based on content type
                if content_type == "json":
                    request_json = data
                    headers['Content-Type'] = 'application/json'
                elif content_type == "form":
                    request_data = data
                    headers['Content-Type'] = 'application/x-www-form-urlencoded'
                else:  # raw
                    request_data = str(data)
                    headers['Content-Type'] = 'text/plain'
            elif isinstance(data, str):
                # String input - handle as before
                # Auto-detect JSON if data looks like JSON and content_type is "form"
                if content_type == "form" and data.strip().startswith('{') and data.strip().endswith('}'):
                    try:
                        import json
                        request_json = json.loads(data)
                        content_type = "json"  # Auto-switch to JSON
                        headers['Content-Type'] = 'application/json'
                    except json.JSONDecodeError:
                        pass  # Not valid JSON, continue with form processing
                
                if method.upper() == "POST" and data:
                    if content_type == "json":
                        # Data is already parsed above or should be parsed here
                        if request_json is None:
                            try:
                                import json
                                request_json = json.loads(data)
                                headers['Content-Type'] = 'application/json'
                            except json.JSONDecodeError:
                                return f"Error: Invalid JSON data for content_type='json': {data}"
                    elif content_type == "raw":
                        request_data = data
                        headers['Content-Type'] = 'text/plain'
                    else:  # form
                        # Parse data as form data (key=value pairs)
                        form_data = {}
                        if data:
                            try:
                                from urllib.parse import parse_qs
                                # Parse as query string
                                parsed = parse_qs(data, keep_blank_values=True)
                                # Convert lists to single values for simple form data
                                for key, values in parsed.items():
                                    form_data[key] = values[0] if values else ""
                            except Exception as e:
                                return f"Error: Invalid form data format: {data}. Use key=value&key2=value2 format."
                        request_data = form_data
                        headers['Content-Type'] = 'application/x-www-form-urlencoded'
            
            # Make request
            client = get_or_create_session(session_id)
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                if request_json is not None:
                    response = client.post(url, headers=headers, json=request_json)
                else:
                    response = client.post(url, headers=headers, data=request_data)
            else:
                return f"Error: Unsupported method {method}"
            
            # Always extract CSRF tokens from response and store them
            csrf_tokens = {}
            csrf_patterns = [
                (r'<input[^>]*name="csrf_token"[^>]*value="([^"]+)"', "csrf_token"),
                (r'<input[^>]*name="_token"[^>]*value="([^"]+)"', "_token"),
                (r'<input[^>]*name="csrf"[^>]*value="([^"]+)"', "csrf"),
                (r'<input[^>]*name="authenticity_token"[^>]*value="([^"]+)"', "authenticity_token"),
                (r'<meta\s+name="csrf-token"\s+content="([^"]+)"', "csrf-token"),
                (r'"csrf_token":\s*"([^"]+)"', "csrf_token"),
            ]
            
            for pattern, token_name in csrf_patterns:
                matches = re.findall(pattern, response.text, re.IGNORECASE)
                if matches:
                    csrf_tokens[token_name] = matches[0]  # Use first match
            
            # Store extracted CSRF tokens for this session
            if csrf_tokens:
                store_csrf(session_id, csrf_tokens)
            
            # Format response
            result = f"Status Code: {response.status_code}\n\n"
            
            # Show redirect history if redirects occurred
            if len(response.history) > 0:
                result += f"Redirects:\n"
                for i, resp in enumerate(response.history, 1):
                    result += f"  {i}. {resp.status_code} {resp.url}\n"
                    if 'location' in resp.headers:
                        result += f"     → Location: {resp.headers['location']}\n"
                result += f"  Final URL: {response.url}\n\n"
            
            result += f"Headers:\n"
            for key, value in response.headers.items():
                result += f"  {key}: {value}\n"
            
            # Show newly set cookies from this response
            new_cookies = dict(response.cookies)
            if new_cookies:
                result += f"\nNew Cookies Set:\n"
                for name, value in new_cookies.items():
                    result += f"  {name}: {value}\n"
            
            # Show all cookies in the session (persistent state)
            all_cookies = dict(client.cookies)
            if all_cookies:
                result += f"\nAll Session Cookies:\n"
                for name, value in all_cookies.items():
                    # Show full cookie value (important for debugging session issues)
                    result += f"  {name}: {value}\n"
            
            # Show extracted/stored CSRF tokens
            all_stored_csrf = get_stored_csrf(session_id)
            if all_stored_csrf:
                result += f"\nStored CSRF Tokens (auto-injected in future POST requests):\n"
                for name, token in all_stored_csrf.items():
                    result += f"  {name}: {token[:50]}{'...' if len(token) > 50 else ''}\n"
            
            result += f"\nContent Length: {len(response.text)} bytes\n\n"
            result += f"Content:\n{response.text}"
            
            return result
                
        except httpx.TimeoutException:
            return f"Error: Request to {url} timed out"
        except httpx.RequestError as e:
            return f"Error fetching {url}: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
