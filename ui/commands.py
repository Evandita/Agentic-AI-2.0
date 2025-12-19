"""Command parser for user input"""

import re
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class Command:
    """Parsed command"""
    type: str
    value: Optional[str] = None
    args: Optional[List[str]] = None


class CommandParser:
    """Parse user commands"""
    
    COMMANDS = {
        '/agent': r'^/agent\s+(gemini|ollama)$',
        '/model': r'^/model\s+(.+)$',
        '/mode': r'^/mode\s+(web-ctf|web_ctf|webctf)$',
        '/setting': r'^/setting\s+([\w-]+)\s+(.+)$',
        '/help': r'^/help$',
        '/clear': r'^/clear$',
        '/exit': r'^/exit$',
        '/quit': r'^/quit$',
    }
    
    # Available models for different agents
    GEMINI_MODELS = [
        'gemini-2.0-flash',
        'gemini-1.5-pro',
        'gemini-1.5-flash',
    ]
    
    SETTINGS = {
        'truncate': ['on', 'off'],
        'max-iterations': ['1', '5', '10', '15', '20', '50']
    }
    
    @classmethod
    def parse(cls, input_text: str) -> Optional[Command]:
        """
        Parse input text for commands
        Returns Command if input is a command, None otherwise
        """
        input_text = input_text.strip()
        
        for cmd_name, pattern in cls.COMMANDS.items():
            match = re.match(pattern, input_text, re.IGNORECASE)
            if match:
                groups = match.groups()
                args = list(groups) if groups else []
                return Command(
                    type=cmd_name[1:],  # Remove /
                    value=args[0] if args else None,
                    args=args
                )
        
        return None
    
    @classmethod
    def get_command_hint(cls, input_text: str) -> Optional[str]:
        """
        Get a helpful hint for incomplete commands
        Returns None if not a recognized command prefix
        """
        input_text = input_text.strip().lower()
        
        if input_text == '/agent':
            return "Usage: /agent <gemini|ollama>"
        elif input_text == '/model':
            return "Usage: /model <model-name>"
        elif input_text == '/mode':
            return "Usage: /mode <web-ctf>"
        elif input_text.startswith('/setting'):
            parts = input_text.split()
            if len(parts) == 1:
                return "Usage: /setting <truncate|max-iterations|loop-detection> <value>"
            elif len(parts) == 2:
                setting = parts[1]
                if setting == 'truncate':
                    return "Usage: /setting truncate <on|off>"
                elif setting == 'max-iterations':
                    return "Usage: /setting max-iterations <1-100>"
                elif setting == 'loop-detection':
                    return "Usage: /setting loop-detection <on|off>"
                else:
                    return f"Unknown setting: {setting}. Available: truncate, max-iterations, loop-detection"
        
        return None
    
    @classmethod
    def is_command(cls, input_text: str) -> bool:
        """Check if input is a command"""
        return input_text.strip().startswith('/')
    
    @classmethod
    def get_available_commands(cls) -> Dict[str, List[str]]:
        """Get available values for each command"""
        return {
            'agent': ['gemini', 'ollama'],
            'mode': ['web-ctf'],
            'setting': list(cls.SETTINGS.keys()),
        }
    
    @classmethod
    def get_setting_values(cls, setting_name: str) -> List[str]:
        """Get available values for a setting"""
        return cls.SETTINGS.get(setting_name.lower(), [])
    
    @classmethod
    def get_gemini_models(cls) -> List[str]:
        """Get available Gemini models"""
        return cls.GEMINI_MODELS
    
    @classmethod
    def get_help_text(cls) -> str:
        """Get help text for all commands"""
        return """[bold cyan]Available Commands:[/bold cyan]

[yellow]/agent <name>[/yellow]        - Switch to agent (gemini, ollama)
[yellow]/model <name>[/yellow]        - Select LLM model
[yellow]/mode <name>[/yellow]         - Switch to mode (web-ctf)
[yellow]/setting <name> <value>[/yellow] - Configure settings
                            truncate (on|off) - Toggle response truncation

[yellow]/help[/yellow]                - Show this help message
[yellow]/clear[/yellow]               - Clear the screen
[yellow]/exit[/yellow] or [yellow]/quit[/yellow]      - Exit the program

[dim]Note: You must select an agent and mode before starting.[/dim]
"""
