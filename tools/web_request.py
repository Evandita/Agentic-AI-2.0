"""Web content fetching tool"""

import httpx
from typing import Union, Dict, Any
from tools.registry import ToolRegistry

# Global session store for maintaining state across requests
_session_store: Dict[str, httpx.Client] = {}


def get_or_create_session(session_id: str = "default") -> httpx.Client:
    """Get or create a persistent session for maintaining cookies/state"""
    if session_id not in _session_store:
        _session_store[session_id] = httpx.Client(
            timeout=1.0,  # Very short timeout for interruptibility
            follow_redirects=True,
            headers={'User-Agent': 'RedTeamAgent/1.0'}
        )
    return _session_store[session_id]


def clear_session(session_id: str = "default"):
    """Clear a session"""
    if session_id in _session_store:
        _session_store[session_id].close()
        del _session_store[session_id]


def setup_web_tools(registry: ToolRegistry):
    """Register web fetching tools"""
    
    @registry.register(
        name="web_request",
        description="Fetch content from a URL using HTTP GET or POST. Maintains session state (cookies) across requests. Useful for analyzing web applications in CTF challenges.",
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
                },
                "session_id": {
                    "type": "string",
                    "description": "Session ID to maintain cookies/state across requests. Use the same session_id for related requests.",
                    "default": "default"
                },
                "extract_csrf": {
                    "type": "boolean",
                    "description": "Extract CSRF tokens from the response and return them in the result",
                    "default": False
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
        extract_csrf: bool = False
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
            
            # Extract CSRF tokens if requested
            csrf_tokens = {}
            if extract_csrf:
                import re
                # Common CSRF token patterns
                csrf_patterns = [
                    r'name="csrf_token"\s+value="([^"]+)"',
                    r'name="_token"\s+value="([^"]+)"',
                    r'name="csrf"\s+value="([^"]+)"',
                    r'name="__csrf_token"\s+value="([^"]+)"',
                    r'<meta\s+name="csrf-token"\s+content="([^"]+)"',
                    r'"csrf_token":\s*"([^"]+)"',
                ]
                
                for pattern in csrf_patterns:
                    matches = re.findall(pattern, response.text, re.IGNORECASE)
                    if matches:
                        csrf_tokens[f"csrf_token_{len(csrf_tokens)}"] = matches[0]
            
            # Format response
            result = f"Status Code: {response.status_code}\n\n"
            result += f"Headers:\n"
            for key, value in response.headers.items():
                result += f"  {key}: {value}\n"
            result += f"\nContent Length: {len(response.text)} bytes\n\n"
            
            if csrf_tokens:
                result += f"CSRF Tokens Found:\n"
                for name, token in csrf_tokens.items():
                    result += f"  {name}: {token}\n"
                result += "\n"
            
            result += f"Content:\n{response.text}"
            
            return result
                
        except httpx.TimeoutException:
            return f"Error: Request to {url} timed out"
        except httpx.RequestError as e:
            return f"Error fetching {url}: {str(e)}"
        except Exception as e:
            return f"Unexpected error: {str(e)}"


    @registry.register(
        name="analyze_auth_response",
        description="Analyze a web response to determine if authentication/registration was successful. Checks for success indicators, redirects, and new cookies.",
        parameters={
            "type": "object",
            "properties": {
                "response_content": {
                    "type": "string",
                    "description": "The full response content from a web_request call"
                },
                "expected_success_patterns": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of patterns that indicate success (e.g., ['Welcome', 'Login successful', 'redirect'])",
                    "default": []
                }
            },
            "required": ["response_content"]
        }
    )
    def analyze_auth_response(response_content: str, expected_success_patterns: list = None) -> str:
        """Analyze authentication response for success indicators"""
        try:
            if expected_success_patterns is None:
                expected_success_patterns = []
            
            # Default success patterns
            default_patterns = [
                "welcome", "successful", "login", "authenticated", "dashboard", 
                "profile", "account", "logged in", "success", "redirect",
                "thank you", "registration complete", "signup successful"
            ]
            
            all_patterns = default_patterns + [p.lower() for p in expected_success_patterns]
            
            analysis = "Authentication Response Analysis:\n"
            analysis += "=" * 40 + "\n\n"
            
            # Check status code
            status_match = re.search(r"Status Code: (\d+)", response_content)
            if status_match:
                status_code = int(status_match.group(1))
                analysis += f"Status Code: {status_code}\n"
                
                if 200 <= status_code < 300:
                    analysis += "✅ Status indicates success\n"
                elif 300 <= status_code < 400:
                    analysis += "➡️ Status indicates redirect (check Location header)\n"
                elif status_code >= 400:
                    analysis += "❌ Status indicates error\n"
            
            # Check for redirects
            location_match = re.search(r"Location: ([^\n]+)", response_content, re.IGNORECASE)
            if location_match:
                location = location_match.group(1).strip()
                analysis += f"\nRedirect Location: {location}\n"
                if any(keyword in location.lower() for keyword in ["dashboard", "profile", "account", "welcome"]):
                    analysis += "✅ Redirect suggests successful authentication\n"
            
            # Check for new cookies (session/auth cookies)
            cookies_section = ""
            in_cookies = False
            for line in response_content.split('\n'):
                if line.lower().startswith('set-cookie'):
                    in_cookies = True
                    cookies_section += line + "\n"
                elif in_cookies and line.strip() and not line.startswith(' '):
                    break
            
            if cookies_section:
                analysis += f"\nNew Cookies Set:\n{cookies_section}"
                analysis += "✅ New cookies suggest session was created/modified\n"
            
            # Check content for success patterns
            content_lower = response_content.lower()
            found_patterns = []
            
            for pattern in all_patterns:
                if pattern in content_lower:
                    found_patterns.append(pattern)
            
            if found_patterns:
                analysis += f"\nSuccess Indicators Found: {', '.join(found_patterns[:5])}\n"
                if len(found_patterns) > 5:
                    analysis += f"... and {len(found_patterns) - 5} more\n"
                analysis += "✅ Content suggests successful authentication\n"
            else:
                analysis += "\nNo clear success indicators found in content\n"
            
            # Check for common error patterns
            error_patterns = ["error", "invalid", "failed", "incorrect", "wrong", "denied", "forbidden"]
            error_found = []
            
            for pattern in error_patterns:
                if pattern in content_lower:
                    error_found.append(pattern)
            
            if error_found:
                analysis += f"\nError Indicators Found: {', '.join(error_found)}\n"
                analysis += "❌ Content suggests authentication failed\n"
            
            # Overall assessment
            analysis += "\n" + "=" * 40 + "\n"
            analysis += "OVERALL ASSESSMENT:\n"
            
            success_score = 0
            if status_match and 200 <= int(status_match.group(1)) < 400:
                success_score += 1
            if location_match:
                success_score += 1
            if cookies_section:
                success_score += 1
            if found_patterns:
                success_score += 2
            if error_found:
                success_score -= 2
            
            if success_score >= 2:
                analysis += "✅ LIKELY SUCCESSFUL - Proceed with authenticated requests\n"
            elif success_score <= -1:
                analysis += "❌ LIKELY FAILED - Check credentials/form data\n"
            else:
                analysis += "❓ UNCLEAR - Manual inspection recommended\n"
            
            return analysis
            
        except Exception as e:
            return f"Error analyzing auth response: {str(e)}"


    @registry.register(
        name="check_session_status",
        description="Check the current status of a web session, including stored cookies and session state. Use this to verify session continuity across requests.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to check. Defaults to 'default'.",
                    "default": "default"
                }
            }
        }
    )
    def check_session_status(session_id: str = "default") -> str:
        """Check session status"""
        try:
            if session_id not in _session_store:
                return f"Session '{session_id}' does not exist."
            
            client = _session_store[session_id]
            
            # Get cookies
            cookies = dict(client.cookies)
            
            result = f"Session '{session_id}' Status:\n"
            result += f"Active: True\n"
            result += f"Timeout: {client.timeout}s\n"
            result += f"Follow Redirects: {client.follow_redirects}\n\n"
            
            if cookies:
                result += f"Cookies ({len(cookies)}):\n"
                for name, value in cookies.items():
                    result += f"  {name}: {value}\n"
            else:
                result += "No cookies stored.\n"
            
            # Check if client has any recent state
            if hasattr(client, '_transport') and client._transport:
                result += "\nSession has active transport.\n"
            else:
                result += "\nSession transport not initialized.\n"
            
            return result
            
        except Exception as e:
            return f"Error checking session status: {str(e)}"


    @registry.register(
        name="reset_session_cookies",
        description="Reset cookies for a session while keeping the session active. Useful when you want to start fresh but keep the same session ID.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to reset cookies for. Defaults to 'default'.",
                    "default": "default"
                }
            }
        }
    )
    def reset_session_cookies(session_id: str = "default") -> str:
        """Reset cookies for a session"""
        try:
            if session_id not in _session_store:
                return f"Session '{session_id}' does not exist. Use web_request first to create it."
            
            client = _session_store[session_id]
            client.cookies.clear()
            
            return f"Cookies cleared for session '{session_id}'."
            
        except Exception as e:
            return f"Error resetting session cookies: {str(e)}"


    @registry.register(
        name="parse_html_form",
        description="Parse HTML content to extract form information including action URLs, input fields, and their requirements. Useful for understanding registration/login forms.",
        parameters={
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "HTML content containing forms to parse"
                },
                "form_index": {
                    "type": "integer",
                    "description": "Index of the form to parse (0-based, default: 0)",
                    "default": 0
                }
            },
            "required": ["html_content"]
        }
    )
    def parse_html_form(html_content: str, form_index: int = 0) -> str:
        """Parse HTML forms to extract form details"""
        try:
            import re
            from urllib.parse import urljoin
            
            # Find all forms
            form_pattern = r'<form[^>]*>.*?</form>'
            forms = re.findall(form_pattern, html_content, re.IGNORECASE | re.DOTALL)
            
            if not forms:
                return "No forms found in the HTML content."
            
            if form_index >= len(forms):
                return f"Form index {form_index} not found. Available forms: 0-{len(forms)-1}"
            
            form_html = forms[form_index]
            
            # Extract form attributes
            action_match = re.search(r'action=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
            method_match = re.search(r'method=["\']([^"\']*)["\']', form_html, re.IGNORECASE)
            
            action = action_match.group(1) if action_match else ""
            method = method_match.group(1).upper() if method_match else "GET"
            
            # Extract input fields
            input_pattern = r'<input[^>]*>'
            inputs = re.findall(input_pattern, form_html, re.IGNORECASE)
            
            # Extract textarea fields
            textarea_pattern = r'<textarea[^>]*>.*?</textarea>'
            textareas = re.findall(textarea_pattern, form_html, re.IGNORECASE | re.DOTALL)
            
            # Extract select fields
            select_pattern = r'<select[^>]*>.*?</select>'
            selects = re.findall(select_pattern, form_html, re.IGNORECASE | re.DOTALL)
            
            result = f"Form {form_index} Details:\n"
            result += f"Method: {method}\n"
            result += f"Action: {action}\n\n"
            
            result += "Input Fields:\n"
            
            for input_tag in inputs:
                name_match = re.search(r'name=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
                type_match = re.search(r'type=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
                value_match = re.search(r'value=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
                required_match = re.search(r'required', input_tag, re.IGNORECASE)
                placeholder_match = re.search(r'placeholder=["\']([^"\']*)["\']', input_tag, re.IGNORECASE)
                
                name = name_match.group(1) if name_match else ""
                input_type = type_match.group(1) if type_match else "text"
                value = value_match.group(1) if value_match else ""
                required = "REQUIRED" if required_match else ""
                placeholder = placeholder_match.group(1) if placeholder_match else ""
                
                if name:  # Only show inputs with names
                    result += f"  - {name} ({input_type})"
                    if value:
                        result += f" [default: {value}]"
                    if placeholder:
                        result += f" [hint: {placeholder}]"
                    if required:
                        result += f" {required}"
                    result += "\n"
            
            # Add textareas
            for textarea in textareas:
                name_match = re.search(r'name=["\']([^"\']*)["\']', textarea, re.IGNORECASE)
                required_match = re.search(r'required', textarea, re.IGNORECASE)
                placeholder_match = re.search(r'placeholder=["\']([^"\']*)["\']', textarea, re.IGNORECASE)
                
                name = name_match.group(1) if name_match else ""
                required = "REQUIRED" if required_match else ""
                placeholder = placeholder_match.group(1) if placeholder_match else ""
                
                if name:
                    result += f"  - {name} (textarea)"
                    if placeholder:
                        result += f" [hint: {placeholder}]"
                    if required:
                        result += f" {required}"
                    result += "\n"
            
            # Add selects
            for select in selects:
                name_match = re.search(r'name=["\']([^"\']*)["\']', select, re.IGNORECASE)
                required_match = re.search(r'required', select, re.IGNORECASE)
                
                name = name_match.group(1) if name_match else ""
                required = "REQUIRED" if required_match else ""
                
                if name:
                    # Extract options
                    option_pattern = r'<option[^>]*value=["\']([^"\']*)["\'][^>]*>([^<]*)</option>'
                    options = re.findall(option_pattern, select, re.IGNORECASE)
                    
                    result += f"  - {name} (select)"
                    if required:
                        result += f" {required}"
                    result += "\n"
                    
                    for value, text in options:
                        result += f"    * {value}: {text.strip()}\n"
            
            # Look for CSRF tokens in the form
            csrf_patterns = [
                r'name="csrf_token"\s+value="([^"]+)"',
                r'name="_token"\s+value="([^"]+)"',
                r'name="csrf"\s+value="([^"]+)"',
                r'name="__csrf_token"\s+value="([^"]+)"',
            ]
            
            csrf_tokens = []
            for pattern in csrf_patterns:
                matches = re.findall(pattern, form_html, re.IGNORECASE)
                csrf_tokens.extend(matches)
            
            if csrf_tokens:
                result += "\nCSRF Tokens in Form:\n"
                for token in csrf_tokens:
                    result += f"  - {token}\n"
            
            return result
            
        except Exception as e:
            return f"Error parsing HTML form: {str(e)}"


    @registry.register(
        name="clear_web_session",
        description="Clear a web session to reset cookies and state. Useful when starting fresh or switching between different user sessions.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session ID to clear. Defaults to 'default'.",
                    "default": "default"
                }
            }
        }
    )
    def clear_web_session(session_id: str = "default") -> str:
        """Clear a web session"""
        try:
            clear_session(session_id)
            return f"Session '{session_id}' cleared successfully."
        except Exception as e:
            return f"Error clearing session: {str(e)}"


    @registry.register(
        name="extract_csrf_tokens",
        description="Extract CSRF tokens from HTML content. Useful for finding tokens that need to be included in subsequent requests.",
        parameters={
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "HTML content to extract CSRF tokens from"
                }
            },
            "required": ["html_content"]
        }
    )
    def extract_csrf_tokens(html_content: str) -> str:
        """Clear a web session"""
        try:
            clear_session(session_id)
            return f"Session '{session_id}' cleared successfully."
        except Exception as e:
            return f"Error clearing session: {str(e)}"


    @registry.register(
        name="extract_csrf_tokens",
        description="Extract CSRF tokens from HTML content. Useful for finding tokens that need to be included in subsequent requests.",
        parameters={
            "type": "object",
            "properties": {
                "html_content": {
                    "type": "string",
                    "description": "HTML content to extract CSRF tokens from"
                }
            },
            "required": ["html_content"]
        }
    )
    def extract_csrf_tokens(html_content: str) -> str:
        """Extract CSRF tokens from HTML content"""
        try:
            import re
            
            csrf_tokens = {}
            
            # Common CSRF token patterns
            patterns = [
                (r'name="csrf_token"\s+value="([^"]+)"', "csrf_token"),
                (r'name="_token"\s+value="([^"]+)"', "_token"),
                (r'name="csrf"\s+value="([^"]+)"', "csrf"),
                (r'name="__csrf_token"\s+value="([^"]+)"', "__csrf_token"),
                (r'<meta\s+name="csrf-token"\s+content="([^"]+)"', "csrf-token-meta"),
                (r'"csrf_token":\s*"([^"]+)"', "csrf_token_json"),
                (r'<input[^>]*name="[^"]*csrf[^"]*"[^>]*value="([^"]+)"', "csrf_input"),
                (r'<input[^>]*name="[^"]*token[^"]*"[^>]*value="([^"]+)"', "token_input"),
            ]
            
            for pattern, name in patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    for i, token in enumerate(matches):
                        token_name = f"{name}_{i}" if i > 0 else name
                        csrf_tokens[token_name] = token
            
            if not csrf_tokens:
                return "No CSRF tokens found in the provided HTML content."
            
            result = "CSRF Tokens Found:\n"
            for name, token in csrf_tokens.items():
                result += f"  {name}: {token}\n"
            
            return result
            
        except Exception as e:
            return f"Error extracting CSRF tokens: {str(e)}"
