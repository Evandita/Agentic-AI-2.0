"""Base mode class"""

from dataclasses import dataclass


@dataclass
class Mode:
    """Base mode configuration"""
    name: str
    display_name: str
    system_context: str
    description: str
    
    def get_context(self) -> str:
        """Get the system context for this mode"""
        return self.system_context
