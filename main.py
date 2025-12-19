"""
Red Teaming Agentic AI System
Main entry point for the application
"""

import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from config import load_config, check_api_availability
from ui import DisplayManager, CommandParser
from agents import GeminiAgent, OllamaAgent
from tools import create_tool_registry
from modes import get_mode, list_modes
from logger import SessionLogger
from errors import RedTeamError


class RedTeamSystem:
    """Main system orchestrator"""
    
    def __init__(self):
        self.console = Console()
        self.config = None
        self.display = None
        self.availability = {}
        self.current_agent = None
        self.current_mode = None
        self.tool_registry = None
        self.logger = None
    
    def initialize(self):
        """Initialize the system"""
        self.console.print("\n[bold cyan]🛡️  Red Teaming Agentic AI System[/bold cyan]\n")
        
        # Load configuration
        self.console.print("[blue]Loading configuration...[/blue]")
        self.config = load_config()
        
        # Initialize display
        self.display = DisplayManager(self.config)
        
        # Initialize logger
        self.logger = SessionLogger()
        
        # Check API availability
        self.console.print("[blue]Checking API availability...[/blue]")
        self.availability = check_api_availability(self.config)
        
        # Display status
        self._display_system_status()
        
        # Initialize tool registry
        self.tool_registry = create_tool_registry()
        
        # Check if we can proceed
        if not self.availability['gemini'] and not self.availability['ollama']:
            self.display.print_error(
                "No LLM providers available.",
                "Please configure at least one:\n"
                "1. Set GEMINI_API_KEY in .env file\n"
                "2. Start Ollama: ollama serve && ollama pull llama3.1"
            )
            return False
        
        return True
    
    def _display_system_status(self):
        """Display system configuration status"""
        status_lines = []
        
        if self.availability['gemini']:
            status_lines.append("[green]✓[/green] Gemini API: Configured")
        else:
            status_lines.append("[yellow]⚠[/yellow] Gemini API: Not configured")
        
        if self.availability['ollama']:
            status_lines.append(
                f"[green]✓[/green] Ollama: Running ({self.config.ollama_model})"
            )
        else:
            status_lines.append("[yellow]⚠[/yellow] Ollama: Not available")
        
        self.display.print_status(status_lines, "System Status")
    
    def _display_welcome(self):
        """Display welcome message"""
        welcome_text = """Welcome to the Red Teaming AI System!

This system helps you solve CTF challenges using AI agents.

[yellow]Quick Start:[/yellow]
1. Select an agent: [cyan]/agent gemini[/cyan] or [cyan]/agent ollama[/cyan]
2. Select a mode: [cyan]/mode web-ctf[/cyan]
3. Describe your challenge and let the AI solve it!

Type [cyan]/help[/cyan] for more commands.
"""
        self.console.print(Panel(welcome_text, border_style="cyan", padding=(1, 2)))
    
    def select_agent(self, agent_name: str) -> bool:
        """Select an agent"""
        agent_name = agent_name.lower()
        
        if agent_name == 'gemini':
            if not self.availability['gemini']:
                self.display.print_error(
                    "Gemini API not available",
                    "Please set GEMINI_API_KEY in your .env file"
                )
                return False
            
            self.current_agent = GeminiAgent(
                self.config,
                self.tool_registry,
                self.display
            )
            self.console.print("[green]✓[/green] Gemini agent selected")
            self.logger.log_agent_selection("Gemini")
            return True
        
        elif agent_name == 'ollama':
            if not self.availability['ollama']:
                self.display.print_error(
                    "Ollama not available",
                    f"Please start Ollama and pull the model:\n"
                    f"  ollama serve\n"
                    f"  ollama pull {self.config.ollama_model}"
                )
                return False
            
            self.current_agent = OllamaAgent(
                self.config,
                self.tool_registry,
                self.display
            )
            self.console.print("[green]✓[/green] Ollama agent selected")
            self.logger.log_agent_selection("Ollama")
            return True
        
        else:
            self.display.print_error(
                f"Unknown agent: {agent_name}",
                "Available agents: gemini, ollama"
            )
            return False
    
    def select_mode(self, mode_name: str) -> bool:
        """Select a mode"""
        mode = get_mode(mode_name)
        
        if mode is None:
            self.display.print_error(
                f"Unknown mode: {mode_name}",
                f"Available modes: {', '.join(list_modes())}"
            )
            return False
        
        self.current_mode = mode
        self.console.print(f"[green]✓[/green] {mode.display_name} mode selected")
        self.logger.log_mode_selection(mode.name)
        return True
    
    def run_agent(self, objective: str):
        """Run the agent with the given objective"""
        if self.current_agent is None:
            self.display.print_error(
                "No agent selected",
                "Please select an agent first with: /agent gemini or /agent ollama"
            )
            return
        
        if self.current_mode is None:
            self.display.print_error(
                "No mode selected",
                "Please select a mode first with: /mode web-ctf"
            )
            return
        
        try:
            self.display.print_separator()
            self.display.print_header(f"Starting: {objective}")
            
            # Run the agent
            result = self.current_agent.run(
                objective=objective,
                mode_context=self.current_mode.get_context()
            )
            
            # Log the interaction
            self.logger.log_interaction(
                objective,
                result,
                self.current_agent.history
            )
            
            self.display.print_separator()
            
            if not result['success']:
                self.display.print_error(
                    result.get('error', 'Unknown error'),
                    "The agent was unable to complete the objective"
                )
        
        except RedTeamError as e:
            self.display.print_error(str(e))
            self.logger.log_error(str(e))
        except Exception as e:
            self.display.print_error(
                f"Unexpected error: {str(e)}",
                "Please check your configuration and try again"
            )
            self.logger.log_error(f"Unexpected error: {str(e)}")
    
    def interactive_loop(self):
        """Main interactive loop"""
        self._display_welcome()
        
        while True:
            try:
                # Get user input
                user_input = Prompt.ask("\n[cyan]>[/cyan]").strip()
                
                if not user_input:
                    continue
                
                self.logger.log_user_input(user_input)
                
                # Check for commands
                if CommandParser.is_command(user_input):
                    command = CommandParser.parse(user_input)
                    
                    if command is None:
                        self.console.print("[red]Unknown command.[/red] Type /help for available commands.")
                        continue
                    
                    # Handle commands
                    if command.type == 'help':
                        self.console.print(CommandParser.get_help_text())
                    
                    elif command.type == 'agent':
                        self.select_agent(command.value)
                    
                    elif command.type == 'mode':
                        self.select_mode(command.value)
                    
                    elif command.type == 'clear':
                        self.console.clear()
                        self._display_welcome()
                    
                    elif command.type in ['exit', 'quit']:
                        if Confirm.ask("\n[yellow]Are you sure you want to exit?[/yellow]"):
                            break
                    
                    continue
                
                # Not a command - treat as objective
                self.run_agent(user_input)
            
            except KeyboardInterrupt:
                self.console.print("\n\n[yellow]Interrupted by user[/yellow]")
                if Confirm.ask("[yellow]Exit?[/yellow]"):
                    break
                continue
            
            except Exception as e:
                self.display.print_error(
                    f"Unexpected error: {str(e)}",
                    "Please try again or restart the system"
                )
    
    def cleanup(self):
        """Cleanup and shutdown"""
        self.console.print("\n[cyan]Shutting down...[/cyan]")
        
        if self.logger:
            self.logger.close()
            self.console.print(f"[green]✓[/green] Session logs saved")
        
        self.console.print("\n[bold cyan]Thank you for using Red Teaming AI![/bold cyan]\n")


def main():
    """Main entry point"""
    system = RedTeamSystem()
    
    try:
        # Initialize
        if not system.initialize():
            return 1
        
        # Run interactive loop
        system.interactive_loop()
        
        # Cleanup
        system.cleanup()
        
        return 0
    
    except Exception as e:
        system.console.print(f"\n[red bold]Fatal error: {str(e)}[/red bold]\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
