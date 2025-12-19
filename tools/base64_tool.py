"""Base64 encoding/decoding tool"""

import base64
from tools.registry import ToolRegistry


def setup_base64_tools(registry: ToolRegistry):
    """Register base64 tools"""
    
    @registry.register(
        name="base64_decode",
        description="Decode a base64 encoded string to plain text. Useful for decoding encoded data in CTF challenges.",
        parameters={
            "type": "object",
            "properties": {
                "encoded_string": {
                    "type": "string",
                    "description": "The base64 encoded string to decode"
                }
            },
            "required": ["encoded_string"]
        }
    )
    def base64_decode(encoded_string: str) -> str:
        """Decode a base64 encoded string"""
        try:
            # Handle URL-safe base64
            encoded_string = encoded_string.strip()
            
            # Add padding if needed
            missing_padding = len(encoded_string) % 4
            if missing_padding:
                encoded_string += '=' * (4 - missing_padding)
            
            decoded_bytes = base64.b64decode(encoded_string)
            decoded_string = decoded_bytes.decode('utf-8', errors='replace')
            return decoded_string
        except Exception as e:
            return f"Error decoding base64: {str(e)}"
    
    @registry.register(
        name="base64_encode",
        description="Encode a plain text string to base64. Useful for encoding payloads.",
        parameters={
            "type": "object",
            "properties": {
                "plain_string": {
                    "type": "string",
                    "description": "The plain text string to encode"
                }
            },
            "required": ["plain_string"]
        }
    )
    def base64_encode(plain_string: str) -> str:
        """Encode a string to base64"""
        try:
            encoded_bytes = base64.b64encode(plain_string.encode('utf-8'))
            encoded_string = encoded_bytes.decode('utf-8')
            return encoded_string
        except Exception as e:
            return f"Error encoding to base64: {str(e)}"
