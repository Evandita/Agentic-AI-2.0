"""Enhanced input handler with autocomplete support using prompt_toolkit"""

from typing import List, Optional
from rich.console import Console
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.history import InMemoryHistory
from ui.commands import CommandParser


class CommandCompleter(Completer):
    """Custom completer for command autocomplete"""
    
    def __init__(self, input_handler):
        self.input_handler = input_handler
    
    def get_completions(self, document, complete_event):
        """Generate completions based on current input"""
        text = document.text_before_cursor
        word_before_cursor = document.get_word_before_cursor()
        
        # Not a command - no completions
        if not text.startswith('/'):
            return
        
        parts = text.split()
        
        # Complete command names (when typing /... or /ag or /mod etc)
        if len(parts) == 0 or (len(parts) == 1 and ' ' not in text):
            commands = ['/agent', '/model', '/mode', '/setting', '/help', '/clear', '/exit', '/quit']
            for cmd in commands:
                if cmd.startswith(text):
                    yield Completion(cmd, start_position=-len(text), display=cmd)
            return
        
        command = parts[0].lower()
        
        # /agent completions
        if command == '/agent':
            options = ['gemini', 'ollama']
            if len(parts) == 1:
                for opt in options:
                    yield Completion(opt, start_position=0)
            elif len(parts) == 2 and not text.endswith(' '):
                current = parts[1]
                for opt in options:
                    if opt.startswith(current.lower()):
                        yield Completion(opt, start_position=-len(current))
        
        # /mode completions
        elif command == '/mode':
            options = ['web-ctf']
            if len(parts) == 1:
                for opt in options:
                    yield Completion(opt, start_position=0)
            elif len(parts) == 2 and not text.endswith(' '):
                current = parts[1]
                for opt in options:
                    if opt.startswith(current.lower()):
                        yield Completion(opt, start_position=-len(current))
        
        # /model completions
        elif command == '/model':
            models = self.input_handler.get_model_suggestions()
            if len(parts) == 1:
                for model in models:
                    yield Completion(model, start_position=0)
            elif len(parts) == 2 and not text.endswith(' '):
                current = parts[1]
                for model in models:
                    if model.startswith(current):
                        yield Completion(model, start_position=-len(current))
        
        # /setting completions
        elif command == '/setting':
            if len(parts) == 1:
                yield Completion('truncate', start_position=0)
                yield Completion('max-iterations', start_position=0)
                yield Completion('loop-detection', start_position=0)
            elif len(parts) == 2:
                current = parts[1]
                if not text.endswith(' '):
                    if 'truncate'.startswith(current.lower()):
                        yield Completion('truncate', start_position=-len(current))
                    elif 'max-iterations'.startswith(current.lower()):
                        yield Completion('max-iterations', start_position=-len(current))
                    elif 'loop-detection'.startswith(current.lower()):
                        yield Completion('loop-detection', start_position=-len(current))
                else:
                    # Show values
                    if current.lower() == 'truncate':
                        for val in ['on', 'off']:
                            yield Completion(val, start_position=0)
                    elif current.lower() == 'loop-detection':
                        for val in ['on', 'off']:
                            yield Completion(val, start_position=0)
            elif len(parts) == 3 and not text.endswith(' '):
                setting_name = parts[1].lower()
                current = parts[2]
                if setting_name == 'truncate':
                    for val in ['on', 'off']:
                        if val.startswith(current.lower()):
                            yield Completion(val, start_position=-len(current))
                elif setting_name == 'loop-detection':
                    for val in ['on', 'off']:
                        if val.startswith(current.lower()):
                            yield Completion(val, start_position=-len(current))


class EnhancedInput:
    """Enhanced input handler with autocomplete and command history"""
    
    def __init__(self, available_ollama_models: Optional[List[str]] = None):
        self.console = Console()
        self.available_ollama_models = available_ollama_models or []
        self.available_gemini_models = CommandParser.get_gemini_models()
        self.current_agent = None
        
        # Setup prompt_toolkit session with history and autocomplete
        self.history = InMemoryHistory()
        self.completer = CommandCompleter(self)
        self.session = PromptSession(
            history=self.history,
            completer=self.completer,
            complete_while_typing=True  # Show completions while typing
        )
    
    def set_current_agent(self, agent: str):
        """Set the currently selected agent"""
        self.current_agent = agent.lower()
    
    def get_model_suggestions(self) -> List[str]:
        """Get available models based on current agent"""
        if self.current_agent == 'gemini':
            return self.available_gemini_models
        elif self.current_agent == 'ollama':
            return self.available_ollama_models
        return []
    
    def prompt_with_suggestions(self, prompt_text: str = "> ") -> str:
        """
        Prompt for input with tab completion and history support
        Uses prompt_toolkit for professional autocomplete
        """
        try:
            # Use prompt_toolkit for input (supports tab completion and history)
            user_input = self.session.prompt(prompt_text).strip()
            
            # Handle special commands
            if user_input == '?':
                self.console.print(CommandParser.get_help_text())
                return self.prompt_with_suggestions(prompt_text)
            
            return user_input
            
        except EOFError:
            # Handle Ctrl+D
            return '/exit'
        except KeyboardInterrupt:
            # Handle Ctrl+C
            self.console.print()
            return ''


