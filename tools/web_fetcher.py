"""Web content fetching tool"""

import httpx
from tools.registry import ToolRegistry


def setup_web_tools(registry: ToolRegistry):
    """Register web fetching tools"""
    
    @registry.register(
        name="fetch_web_content",
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
                    "type": "string",
                    "description": "Optional data to send in POST request body",
                    "default": ""
                }
            },
            "required": ["url"]
        }
    )
    def fetch_web_content(
        url: str,
        method: str = "GET",
        headers: dict = None,
        data: str = ""
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
            
            # Make request
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                if method.upper() == "GET":
                    response = client.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = client.post(url, headers=headers, data=data)
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
