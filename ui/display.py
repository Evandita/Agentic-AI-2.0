"""Display manager for Red Teaming AI system using Rich"""

from rich.console import Console, Group
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.text import Text
from typing import Optional, Any
import json
from config import AgentConfig


class DisplayManager:
    """
    Manages display formatting with dynamic width
    """
    
    def __init__(self, config: AgentConfig, truncation_enabled: bool = True):
        self.console = Console()
        self.config = config
        self.truncation_enabled = truncation_enabled
        
        # Determine effective width
        if config.console_width == "auto":
            self.frame_width = self.console.width
        else:
            try:
                self.frame_width = int(config.console_width)
            except ValueError:
                self.frame_width = self.console.width
        
        # Ensure minimum width
        if self.frame_width < 40:
            self.console.print(
                "[yellow]Warning:[/yellow] Terminal is very narrow.\n"
                "For best experience, resize to at least 80 characters wide."
            )
            self.frame_width = 40
    
    def set_truncation(self, enabled: bool):
        """Update truncation setting"""
        self.truncation_enabled = enabled
    
    def get_panel_width(self) -> int:
        """
        Get width for panels (accounting for borders and padding)
        """
        return max(self.frame_width - 4, 40)
    
    def get_text_width(self) -> int:
        """
        Get width for text wrapping inside panels
        """
        return max(self.get_panel_width() - 4, 36)
    
    def update_width(self):
        """
        Recalculate width (call if terminal is resized)
        """
        if self.config.console_width == "auto":
            self.frame_width = Console().width
            if self.frame_width < 40:
                self.frame_width = 40
    
    def print_panel(
        self,
        content: str,
        title: str,
        border_style: str = "cyan",
        expand: bool = True
    ):
        """
        Print a panel with proper width
        """
        panel = Panel(
            content,
            title=title,
            border_style=border_style,
            width=self.frame_width if expand else None,
            padding=(1, 2)
        )
        self.console.print(panel)
    
    def print_thinking(self, content: str, step: Optional[int] = None):
        """Display agent thinking/reasoning"""
        title = f"🧠 Agent Thinking" + (f" (Step {step})" if step else "")
        self.print_panel(content, title, border_style="cyan")
    
    def print_tool_call(self, tool_name: str, tool_input: dict, step: Optional[int] = None):
        """Display tool being called"""
        title = f"🔧 Tool Execution" + (f" (Step {step})" if step else "")
        
        # Make it very clear what tool is being used
        content = f"[bold yellow]Calling Tool:[/bold yellow] [bold white]{tool_name}[/bold white]\n\n"
        content += f"[bold yellow]Parameters:[/bold yellow]\n"
        
        # Format the input nicely
        if tool_input:
            for key, value in tool_input.items():
                # Truncate very long values if truncation is enabled
                value_str = str(value)
                if self.truncation_enabled and len(value_str) > 100:
                    value_str = value_str[:100] + "..."
                content += f"  • {key}: {value_str}\n"
        else:
            content += "  (no parameters)\n"
        
        self.print_panel(content, title, border_style="yellow")
    
    def print_tool_response(self, tool_name: str, result: str, step: Optional[int] = None):
        """Display tool response"""
        title = f"📊 Tool Response" + (f" (Step {step})" if step else "")
        
        # Show which tool responded
        content = f"[bold green]Tool:[/bold green] [bold white]{tool_name}[/bold white]\n"
        content += f"[bold green]Status:[/bold green] ✓ Executed successfully\n\n"
        content += f"[bold green]Output:[/bold green]\n"
        
        # Truncate very long responses if truncation is enabled
        display_result = result
        if self.truncation_enabled:
            max_length = 1000
            if len(result) > max_length:
                display_result = result[:max_length] + f"\n\n[dim]... (truncated, total length: {len(result)} chars)[/dim]"
        
        content += display_result
        
        self.print_panel(content, title, border_style="green")
    
    def print_final_answer(self, answer: str):
        """Display final answer"""
        self.print_panel(answer, "🎯 Final Answer", border_style="green bold")
    
    def print_error(self, error_msg: str, suggestion: Optional[str] = None):
        """Display error message"""
        content = f"[red]Error:[/red]\n{error_msg}"
        if suggestion:
            content += f"\n\n[yellow]Suggestion:[/yellow]\n{suggestion}"
        self.print_panel(content, "❌ Error", border_style="red")
    
    def print_status(self, status_lines: list[str], title: str = "Status"):
        """Display status information"""
        content = "\n".join(status_lines)
        self.print_panel(content, title, border_style="blue")
    
    def print_separator(self):
        """Print a separator line"""
        self.console.print("─" * self.frame_width, style="dim")
    
    def print_header(self, text: str):
        """Print a header"""
        self.console.print(f"\n[bold cyan]{text}[/bold cyan]\n")
