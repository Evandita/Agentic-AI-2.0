"""
Red Teaming Agentic AI System
Main entry point for the application
"""

import sys
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

from config import load_config, check_api_availability, get_available_ollama_models
from ui import DisplayManager, CommandParser, EnhancedInput
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
        self.current_agent_type = None
        self.current_model = None
        self.current_mode = None
        self.tool_registry = None
        self.logger = None
        self.input_handler = None
        self.available_ollama_models = []
        self.truncation_enabled = True
        self.max_iterations = 10  # Default max iterations for agents
    
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
        
        # Detect available Ollama models if available
        if self.availability['ollama']:
            self.console.print("[blue]Detecting available Ollama models...[/blue]")
            self.available_ollama_models = get_available_ollama_models(self.config.ollama_base_url)
        
        # Initialize enhanced input with autocomplete (pass detected models)
        self.input_handler = EnhancedInput(self.available_ollama_models)
        
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
            if self.available_ollama_models:
                models_str = ", ".join(self.available_ollama_models[:3])
                if len(self.available_ollama_models) > 3:
                    models_str += f", +{len(self.available_ollama_models) - 3} more"
                status_lines.append(
                    f"[green]✓[/green] Ollama: Running\n  [dim]Available models:[/dim] {models_str}"
                )
            else:
                status_lines.append("[yellow]⚠[/yellow] Ollama: Running but no models found")
        else:
            status_lines.append("[yellow]⚠[/yellow] Ollama: Not available")
        
        self.display.print_status(status_lines, "System Status")
    
    def _display_welcome(self):
        """Display welcome message"""
        welcome_text = """Welcome to the Red Teaming AI System!

This system helps you solve CTF challenges using AI agents.

[yellow]Quick Start:[/yellow]
1. Select an agent: [cyan]/agent gemini[/cyan] or [cyan]/agent ollama[/cyan]
2. Select a model: [cyan]/model <model-name>[/cyan] (optional, uses default if not set)
3. Select a mode: [cyan]/mode web-ctf[/cyan]
4. Describe your challenge and let the AI solve it!

[yellow]Available Commands:[/yellow]
• [cyan]/agent <name>[/cyan]  - Switch agent (gemini, ollama)
• [cyan]/model <name>[/cyan]  - Select LLM model
• [cyan]/mode <name>[/cyan]   - Switch mode (web-ctf)
• [cyan]/setting <name> <value>[/cyan] - Configure settings (truncate, max-iterations)
• [cyan]/help[/cyan]          - Show detailed help
• [cyan]/clear[/cyan]         - Clear screen
• [cyan]/exit[/cyan]          - Exit program
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
                self.display,
                max_iterations=self.max_iterations,
                logger=self.logger
            )
            self.current_agent_type = 'gemini'
            self.input_handler.set_current_agent('gemini')
            self.console.print("[green]✓[/green] Gemini agent selected")
            self.logger.log_agent_selection("Gemini")
            return True
        
        elif agent_name == 'ollama':
            if not self.availability['ollama']:
                self.display.print_error(
                    "Ollama not available",
                    f"Please start Ollama and pull the model:\n"
                    f"  ollama serve"
                )
                return False
            
            self.current_agent = OllamaAgent(
                self.config,
                self.tool_registry,
                self.display,
                max_iterations=self.max_iterations,
                logger=self.logger
            )
            self.current_agent_type = 'ollama'
            self.input_handler.set_current_agent('ollama')
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
    
    def select_model(self, model_name: str) -> bool:
        """Select a model for the current agent"""
        if not self.current_agent_type:
            self.display.print_error(
                "No agent selected",
                "Please select an agent first with: /agent gemini or /agent ollama"
            )
            return False
        
        # Validate model based on agent type
        if self.current_agent_type == 'gemini':
            available_models = CommandParser.get_gemini_models()
            if model_name not in available_models:
                self.display.print_error(
                    f"Unknown Gemini model: {model_name}",
                    f"Available models: {', '.join(available_models)}"
                )
                return False
        
        elif self.current_agent_type == 'ollama':
            if model_name not in self.available_ollama_models:
                self.display.print_error(
                    f"Model not available: {model_name}",
                    f"Available models: {', '.join(self.available_ollama_models)}"
                )
                return False
        
        self.current_model = model_name
        
        # Update the agent's model
        if self.current_agent:
            self.current_agent.update_model(model_name)
        
        self.console.print(f"[green]✓[/green] Model selected: {model_name}")
        self.logger.log_user_input(f"Model selected: {model_name}")
        return True
    
    def configure_setting(self, setting_name: str, value: str) -> bool:
        """Configure a setting"""
        setting_name = setting_name.lower()
        
        if setting_name == 'truncate':
            value = value.lower()
            if value == 'on':
                self.truncation_enabled = True
                self.console.print("[green]✓[/green] Response truncation: ON")
            elif value == 'off':
                self.truncation_enabled = False
                self.console.print("[green]✓[/green] Response truncation: OFF")
            else:
                self.display.print_error(
                    f"Invalid value for truncate: {value}",
                    "Available values: on, off"
                )
                return False
            
            self.logger.log_user_input(f"Setting changed: truncate={value}")
            return True
        
        elif setting_name == 'max-iterations':
            try:
                iterations = int(value)
                if iterations < 1 or iterations > 100:
                    self.display.print_error(
                        f"Invalid value for max-iterations: {value}",
                        "Valid range: 1-100 iterations"
                    )
                    return False
                
                self.max_iterations = iterations
                
                # Update current agent if one is selected
                if self.current_agent:
                    self.current_agent.max_iterations = iterations
                
                self.console.print(f"[green]✓[/green] Max iterations set to: {iterations}")
                self.logger.log_user_input(f"Setting changed: max-iterations={iterations}")
                return True
            except ValueError:
                self.display.print_error(
                    f"Invalid value for max-iterations: {value}",
                    "Please provide a number between 1-100"
                )
                return False
        
        else:
            self.display.print_error(
                f"Unknown setting: {setting_name}",
                f"Available settings: truncate, max-iterations"
            )
            return False

    
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
                # Get user input with suggestions
                user_input = self.input_handler.prompt_with_suggestions("\n> ").strip()
                
                if not user_input:
                    continue
                
                self.logger.log_user_input(user_input)
                
                # Check for commands
                if CommandParser.is_command(user_input):
                    command = CommandParser.parse(user_input)
                    
                    if command is None:
                        # Try to provide helpful hint for incomplete commands
                        hint = CommandParser.get_command_hint(user_input)
                        if hint:
                            self.console.print(f"[yellow]{hint}[/yellow]")
                        else:
                            self.console.print("[red]Unknown command.[/red] Type /help for available commands.")
                        continue
                    
                    # Handle commands
                    if command.type == 'help':
                        self.console.print(CommandParser.get_help_text())
                    
                    elif command.type == 'agent':
                        self.select_agent(command.value)
                    
                    elif command.type == 'model':
                        if command.value:
                            self.select_model(command.value)
                        else:
                            models = self.input_handler.get_model_suggestions()
                            if models:
                                self.console.print("[yellow]Available models:[/yellow]")
                                for m in models:
                                    self.console.print(f"  {m}")
                            else:
                                self.display.print_error("No models available", "Select an agent first")
                    
                    elif command.type == 'mode':
                        self.select_mode(command.value)
                    
                    elif command.type == 'setting':
                        if len(command.args) >= 2:
                            self.configure_setting(command.args[0], command.args[1])
                        else:
                            self.display.print_error(
                                "Invalid setting syntax",
                                "Use: /setting <truncate|max-iterations> <value>"
                            )
                    
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
