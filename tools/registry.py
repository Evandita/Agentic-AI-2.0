"""Tool registry for managing available tools"""

from typing import Callable, Dict, Any
from dataclasses import dataclass


@dataclass
class ToolDefinition:
    """Tool definition with metadata"""
    name: str
    description: str
    parameters: Dict[str, Any]
    function: Callable


class ToolRegistry:
    """Registry for tools with decorator-based registration"""
    
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
    
    def register(self, name: str, description: str, parameters: Dict[str, Any]):
        """
        Decorator to register a tool
        
        Usage:
            @registry.register(
                name="tool_name",
                description="Tool description",
                parameters={...}
            )
            def tool_function(...):
                ...
        """
        def decorator(func: Callable):
            self.tools[name] = ToolDefinition(
                name=name,
                description=description,
                parameters=parameters,
                function=func
            )
            return func
        return decorator
    
    def execute(self, name: str, **kwargs) -> Any:
        """Execute a tool by name"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        
        tool = self.tools[name]
        return tool.function(**kwargs)
    
    def get_tool_function(self, name: str) -> Callable:
        """Get the tool function by name"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        
        return self.tools[name].function
    
    def get_schemas(self) -> list[Dict[str, Any]]:
        """Get tool schemas for LLM function calling"""
        schemas = []
        for tool in self.tools.values():
            schemas.append({
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            })
        return schemas
    
    def get_tool_names(self) -> list[str]:
        """Get list of available tool names"""
        return list(self.tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if tool exists"""
        return name in self.tools
    
    def get_tool_function(self, name: str) -> Callable:
        """Get the tool function by name"""
        if name not in self.tools:
            raise ValueError(f"Unknown tool: {name}")
        return self.tools[name].function
