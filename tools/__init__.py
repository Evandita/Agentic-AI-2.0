"""Initialize tools package and create default registry"""

from tools.registry import ToolRegistry, ToolDefinition
from tools.base64_tool import setup_base64_tools
from tools.web_request import setup_web_tools


def create_tool_registry() -> ToolRegistry:
    """Create and populate a tool registry with all available tools"""
    registry = ToolRegistry()
    
    # Register all tools
    setup_base64_tools(registry)
    setup_web_tools(registry)
    
    return registry


__all__ = ['ToolRegistry', 'ToolDefinition', 'create_tool_registry']
