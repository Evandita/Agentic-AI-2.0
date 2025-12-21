"""Web content fetching tool"""

import httpx
from typing import Union
from tools.registry import ToolRegistry


def setup_web_tools(registry: ToolRegistry):
    """Register web fetching tools"""
    
    @registry.register(
        name="web_request",
        description="Fetch content from a URL using HTTP GET or POST. Returns the response text, headers, and status code. Useful for analyzing web applications in CTF challenges.",
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
                    "description": "Optional HTTP headers as key-value pairs",
                    "default": {}
                },
                "data": {
                    "oneOf": [
                        {"type": "string"},
                        {"type": "object"}
                    ],
                    "description": "Data to send in POST request. Can be a string (parsed based on content_type) or a dict (sent as form data or JSON depending on content_type)"
                },
                "content_type": {
                    "type": "string",
                    "enum": ["form", "json", "raw"],
                    "description": "How to send the data: 'form' for form-encoded, 'json' for JSON, 'raw' for raw string",
                    "default": "form"
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
        content_type: str = "form"
    ) -> str:
        """Fetch web content"""
        try:
            # Validate URL
            if not url.startswith(('http://', 'https://')):
                return "Error: URL must start with http:// or https://"
            
            # Set default headers
            if headers is None:
                headers = {}
            
            # Add user agent if not provided
            if 'User-Agent' not in headers:
                headers['User-Agent'] = 'RedTeamAgent/1.0'
            
            # Prepare data based on content type
            request_data = None
            request_json = None
            
            # Handle different data input types
            if isinstance(data, dict):
                # Dict input
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
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=headers)
                elif method.upper() == "POST":
                    if request_json is not None:
                        response = client.post(url, headers=headers, json=request_json)
                    else:
                        response = client.post(url, headers=headers, data=request_data)
                else:
                    return f"Error: Unsupported method {method}"
                
                # Format response
                result = f"Status Code: {response.status_code}\n\n"
                result += f"Headers:\n"
                for key, value in response.headers.items():
                    result += f"  {key}: {value}\n"
                result += f"\nContent Length: {len(response.text)} bytes\n\n"
                result += f"Content:\n{response.text}"
                
                return result
                
        except httpx.TimeoutException:
            return f"Error: Request to {url} timed out"
        except httpx.RequestError as e:
            return f"Error fetching {url}: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"
