"""Command parser for user input"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class Command:
    """Parsed command"""
    type: str
    value: Optional[str] = None


class CommandParser:
    """Parse user commands"""
    
    COMMANDS = {
        '/agent': r'^/agent\s+(gemini|ollama)(?:\s+(.*))?$',
        '/mode': r'^/mode\s+(web-ctf|web_ctf|webctf)$',
        '/help': r'^/help$',
        '/clear': r'^/clear$',
        '/exit': r'^/exit$',
        '/quit': r'^/quit$',
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
                return Command(
                    type=cmd_name[1:],  # Remove /
                    value=groups[0] if groups and groups[0] else None
                )
        
        return None
    
    @classmethod
    def is_command(cls, input_text: str) -> bool:
        """Check if input is a command"""
        return input_text.strip().startswith('/')
    
    @classmethod
    def get_help_text(cls) -> str:
        """Get help text for all commands"""
        return """[bold cyan]Available Commands:[/bold cyan]

[yellow]/agent gemini[/yellow]   - Switch to Gemini agent
[yellow]/agent ollama[/yellow]   - Switch to Ollama agent

[yellow]/mode web-ctf[/yellow]   - Switch to Web CTF mode

[yellow]/help[/yellow]           - Show this help message
[yellow]/clear[/yellow]          - Clear the screen
[yellow]/exit[/yellow] or [yellow]/quit[/yellow] - Exit the program

[dim]Note: You must select an agent and mode before starting.[/dim]
"""
