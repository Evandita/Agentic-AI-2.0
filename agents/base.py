"""Base agent implementation with ReAct loop"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re
import json
import threading
import time
from tools.registry import ToolRegistry
from ui.display import DisplayManager
from errors import ToolExecutionError


@dataclass
class AgentStep:
    """Single step in ReAct loop"""
    thought: str
    action: Optional[str]
    action_input: Optional[Dict[str, Any]]
    observation: Optional[str]
    step_number: int
    is_final: bool = False
    final_answer: Optional[str] = None


class BaseAgent:
    """
    Base agent with synchronous ReAct loop
    """
    
    def __init__(
        self,
        name: str,
        tool_registry: ToolRegistry,
        display: DisplayManager,
        max_iterations: int = 10,
        logger: Optional[Any] = None,
        loop_detection_enabled: bool = True
    ):
        self.name = name
        self.tools = tool_registry
        self.display = display
        self.max_iterations = max_iterations
        self.history: List[AgentStep] = []
        self.logger = logger
        self.step_counter = 0
        self.loop_detection_enabled = loop_detection_enabled
        
        # Pause/resume support
        self._pause_event = threading.Event()
        self._pause_event.set()  # Start unpaused
        self._additional_context = ""
        self._is_paused = False
        self._output_suppressed = False
        self._current_iteration = 0  # Track current iteration across pause/resume
    
    def pause(self):
        """Pause the agent execution"""
        self._is_paused = True
        self._output_suppressed = True
        self._pause_event.clear()
    
    def resume(self, additional_context: str = ""):
        """Resume the agent execution with optional additional context"""
        self._additional_context = additional_context
        self._is_paused = False
        self._output_suppressed = False
        self._pause_event.set()
    
    def is_paused(self) -> bool:
        """Check if agent is currently paused"""
        return self._is_paused
    
    def _should_suppress_output(self) -> bool:
        """Check if output should be suppressed due to pause"""
        return self._is_paused or self._output_suppressed
    
    def _print_thinking(self, thought: str, iteration: int):
        """Print thinking with pause check"""
        if not self._should_suppress_output():
            self.display.print_thinking(thought, iteration)
    
    def _print_tool_call(self, action_name: str, action_input: dict, iteration: int):
        """Print tool call with pause check"""
        if not self._should_suppress_output():
            self.display.print_tool_call(action_name, action_input, iteration)
    
    def _print_tool_response(self, action_name: str, observation: str, iteration: int):
        """Print tool response with pause check"""
        if not self._should_suppress_output():
            self.display.print_tool_response(action_name, observation, iteration)
    
    def _print_final_answer(self, final_answer: str):
        """Print final answer with pause check"""
        if not self._should_suppress_output():
            self.display.print_final_answer(final_answer)
    
    def _print_error(self, error_msg: str, suggestion: str = None):
        """Print error with pause check"""
        if not self._should_suppress_output():
            self.display.print_error(error_msg, suggestion)
    
    def run(self, objective: str, mode_context: str = "") -> Dict[str, Any]:
        """
        Execute the ReAct loop synchronously
        
        Returns:
            {
                'success': bool,
                'result': str,
                'steps': List[AgentStep]
            }
        """
        
        # Initialize conversation
        system_prompt = self._get_system_prompt(mode_context)
        
        # Only reset history and conversation if this is a fresh start (not resuming)
        if not hasattr(self, '_is_resuming') or not self._is_resuming:
            self.history = []
            conversation_history = []
            self._current_iteration = 0
        else:
            # We're resuming, so we keep existing history and conversation
            conversation_history = getattr(self, '_conversation_history', [])
            self._is_resuming = False
        
        for iteration in range(self._current_iteration, self.max_iterations):
            self._current_iteration = iteration + 1
            
            # Add additional context at the start if provided (from resume/interrupt)
            if hasattr(self, '_additional_context') and self._additional_context:
                conversation_history.append({
                    "role": "user", 
                    "content": self._additional_context
                })
                self._additional_context = ""  # Clear after use
            
            # Check for pause at the start of each iteration
            if self._is_paused:
                # Save current state for resume
                self._conversation_history = conversation_history
                self._is_resuming = True
                self._pause_event.wait()  # Wait until resumed
                # Incorporate additional context if provided
                if self._additional_context:
                    # Add the additional context to the conversation
                    conversation_history.append({
                        "role": "user", 
                        "content": f"Additional context from user: {self._additional_context}"
                    })
                    self._additional_context = ""  # Clear after use
            
            try:
                # Build prompt for this iteration
                if iteration == 0:
                    prompt = f"{system_prompt}\n\nObjective: {objective}\n\nLet's solve this step by step."
                else:
                    # Check if there were recent errors in conversation history
                    recent_errors = []
                    # Get errors that occurred after the last assistant message
                    found_last_assistant = False
                    for msg in reversed(conversation_history):
                        if msg['role'] == 'assistant':
                            found_last_assistant = True
                            break
                        elif msg['role'] == 'user' and msg['content'].startswith('Error:'):
                            recent_errors.insert(0, msg['content'])
                    
                    error_context = ""
                    if recent_errors:
                        error_context = "\n\n".join(recent_errors) + "\n\n"
                    
                    # Add previous observation with format reminder
                    if len(self.history) > 0:
                        last_step = self.history[-1]
                        prompt = f"{error_context}Observation: {last_step.observation}\n\nWhat's your next step? Use the format:\nThought: [reasoning]\nAction: [tool_name]\nAction Input: {{\"param\": \"value\"}}\n\nOr if you have the answer:\nThought: [reasoning]\nFinal Answer: [answer]"
                    else:
                        # No history yet, re-prompt with objective
                        prompt = f"{error_context}Objective: {objective}\n\nYou MUST use this format:\nThought: [reasoning]\nAction: [tool_name]\nAction Input: {{\"param\": \"value\"}}"
                
                # Check for pause before LLM call
                if self._is_paused:
                    self._pause_event.wait()
                    if self._additional_context:
                        conversation_history.append({
                            "role": "user", 
                            "content": f"Additional context from user: {self._additional_context}"
                        })
                        self._additional_context = ""
                
                # Check for pause before LLM call
                if self._is_paused:
                    # Save current state for resume
                    self._conversation_history = conversation_history
                    self._is_resuming = True
                    self._pause_event.wait()
                    if self._additional_context:
                        conversation_history.append({
                            "role": "user", 
                            "content": f"Additional context from user: {self._additional_context}"
                        })
                        self._additional_context = ""
                
                # Get response from LLM
                response = self._call_llm(prompt, conversation_history)
                
                # Truncate at second "Thought:" to prevent multi-step hallucination
                response = self._truncate_multi_step(response)
                
                conversation_history.append({"role": "assistant", "content": response})
                
                # Parse response
                parsed = self._parse_response(response)
                
                # Check for parse errors
                if 'error' in parsed:
                    # Debug: print the actual response
                    print(f"\n[DEBUG] Raw LLM Response:\n{response}\n")
                    
                    self._print_error(
                        parsed['error'],
                        "Please use the correct format:\nThought: ...\nAction: tool_name\nAction Input: {\"param\": \"value\"}"
                    )
                    # Give agent another chance with clearer instructions
                    conversation_history.append({
                        "role": "user", 
                        "content": f"Error: {parsed['error']}. You MUST respond with:\nThought: [your reasoning]\nAction: [tool_name]\nAction Input: {{\"param\": \"value\"}}"
                    })
                    continue
                
                # Check if this is a final answer
                if parsed['is_final']:
                    self._print_thinking(parsed['thought'], iteration + 1)
                    self._print_final_answer(parsed['final_answer'])
                    
                    step = AgentStep(
                        thought=parsed['thought'],
                        action=None,
                        action_input=None,
                        observation=None,
                        step_number=iteration + 1,
                        is_final=True,
                        final_answer=parsed['final_answer']
                    )
                    self.history.append(step)
                    
                    # Save conversation history
                    self._conversation_history = conversation_history
                    
                    return {
                        'success': True,
                        'result': parsed['final_answer'],
                        'steps': self.history
                    }
                
                # Display thought
                self._print_thinking(parsed['thought'], iteration + 1)
                
                # Execute action
                action_name = parsed['action']
                action_input = parsed['action_input']
                
                self._print_tool_call(action_name, action_input, iteration + 1)
                
                # Check for pause before tool execution
                if self._is_paused:
                    self._pause_event.wait()
                    if self._additional_context:
                        conversation_history.append({
                            "role": "user", 
                            "content": f"Additional context from user: {self._additional_context}"
                        })
                        self._additional_context = ""
                
                # Check for pause before tool execution
                if self._is_paused:
                    # Save current state for resume
                    self._conversation_history = conversation_history
                    self._is_resuming = True
                    self._pause_event.wait()
                    if self._additional_context:
                        conversation_history.append({
                            "role": "user", 
                            "content": f"Additional context from user: {self._additional_context}"
                        })
                        self._additional_context = ""
                
                # Execute tool
                observation = self._execute_tool(action_name, action_input)
                
                self._print_tool_response(action_name, observation, iteration + 1)
                
                # Record step
                step = AgentStep(
                    thought=parsed['thought'],
                    action=action_name,
                    action_input=action_input,
                    observation=observation,
                    step_number=iteration + 1
                )
                self.history.append(step)
                
                # Save conversation history for potential resume
                self._conversation_history = conversation_history
                
                # Check for loops
                if self._check_infinite_loop():
                    return {
                        'success': False,
                        'error': 'Agent appears to be stuck in a loop',
                        'steps': self.history
                    }
                
            except Exception as e:
                return self._handle_error(e, iteration)
        
        # Max iterations reached
        return {
            'success': False,
            'error': 'Max iterations reached without finding answer',
            'steps': self.history
        }
    
    def _call_llm(self, prompt: str, history: List[Dict]) -> str:
        """
        Call LLM - must be implemented by subclass
        """
        raise NotImplementedError("Subclass must implement _call_llm")
    
    def _truncate_multi_step(self, response: str) -> str:
        """
        Truncate response if it contains multiple Thought/Action sequences.
        This prevents the agent from hallucinating multiple steps.
        """
        # Find all "Thought:" occurrences
        pattern = r'(?:^|\n)\s*Thought:'
        matches = list(re.finditer(pattern, response, re.IGNORECASE | re.MULTILINE))
        
        if len(matches) > 1:
            # Keep only up to the second "Thought:"
            return response[:matches[1].start()].strip()
        
        # Also stop if agent tries to write "Observation:"
        obs_match = re.search(r'\n\s*Observation:', response, re.IGNORECASE)
        if obs_match:
            return response[:obs_match.start()].strip()
        
        return response
    
    def _execute_tool(self, tool_name: str, tool_input: Dict) -> str:
        """Execute tool with interrupt capability using threading"""
        import threading
        import time
        
        try:
            if not self.tools.has_tool(tool_name):
                return f"Error: Unknown tool '{tool_name}'. Available tools: {', '.join(self.tools.get_tool_names())}"
            
            # Validate parameters
            validation_error = self._validate_tool_parameters(tool_name, tool_input)
            if validation_error:
                return validation_error
            
            # Check for pause before tool execution
            if self._is_paused:
                return "Tool execution interrupted by user"
            
            # Result container for thread communication
            result = {"value": None, "error": None, "completed": False}
            
            def tool_worker():
                """Run tool in separate thread"""
                try:
                    tool_result = self.tools.execute(tool_name, **tool_input)
                    result["value"] = str(tool_result)
                    result["completed"] = True
                except Exception as e:
                    result["error"] = str(e)
                    result["completed"] = True
            
            # Start tool execution in background thread
            tool_thread = threading.Thread(target=tool_worker, daemon=True)
            tool_thread.start()
            
            # Wait for completion with pause checks and timeout
            start_time = time.time()
            timeout = 3.0  # 3 second timeout for tools (matches httpx timeout)
            
            while not result["completed"] and (time.time() - start_time) < timeout:
                if self._is_paused:
                    # Signal interruption
                    return "Tool execution interrupted by user"
                time.sleep(0.05)  # Check pause flag every 50ms
            
            # Check if tool completed
            if not result["completed"]:
                # Tool timed out
                return f"Tool execution timed out after {timeout} seconds"
            
            if result["error"]:
                return f"Tool execution error: {result['error']}"
            
            return result["value"] if result["value"] is not None else "Tool completed but returned no result"
            
        except Exception as e:
            return f"Tool execution error: {str(e)}"
    
    def _validate_tool_parameters(self, tool_name: str, tool_input: Dict) -> Optional[str]:
        """Validate tool parameters against schema"""
        tool_def = self.tools.tools[tool_name]
        schema = tool_def.parameters
        
        # Check required parameters
        required = schema.get('required', [])
        for param in required:
            if param not in tool_input:
                return f"Error: Missing required parameter '{param}' for tool '{tool_name}'"
        
        # Check parameter types and values
        properties = schema.get('properties', {})
        for param, value in tool_input.items():
            if param not in properties:
                return f"Error: Unknown parameter '{param}' for tool '{tool_name}'"
            
            param_schema = properties[param]
            
            # Check oneOf types (for parameters that can be multiple types)
            if 'oneOf' in param_schema:
                valid_types = []
                for type_option in param_schema['oneOf']:
                    option_type = type_option.get('type')
                    valid_types.append(option_type)
                
                value_valid = False
                for valid_type in valid_types:
                    if valid_type == 'string' and isinstance(value, str):
                        value_valid = True
                        break
                    elif valid_type == 'object' and isinstance(value, dict):
                        value_valid = True
                        break
                    elif valid_type == 'integer' and isinstance(value, int):
                        value_valid = True
                        break
                    elif valid_type == 'boolean' and isinstance(value, bool):
                        value_valid = True
                        break
                
                if not value_valid:
                    return f"Error: Parameter '{param}' must be one of {valid_types}, got {type(value).__name__}"
            # Basic type checking for simple type parameters
            elif 'type' in param_schema:
                param_type = param_schema['type']
                if param_type == 'string' and not isinstance(value, str):
                    return f"Error: Parameter '{param}' must be a string, got {type(value).__name__}"
                elif param_type == 'integer' and not isinstance(value, int):
                    return f"Error: Parameter '{param}' must be an integer, got {type(value).__name__}"
                elif param_type == 'boolean' and not isinstance(value, bool):
                    return f"Error: Parameter '{param}' must be a boolean, got {type(value).__name__}"
                elif param_type == 'object' and not isinstance(value, dict):
                    return f"Error: Parameter '{param}' must be an object, got {type(value).__name__}"
            
            # Check enum values
            if 'enum' in param_schema:
                allowed_values = param_schema['enum']
                if value not in allowed_values:
                    return f"Error: Parameter '{param}' must be one of {allowed_values}, got '{value}'"
            
            # URL validation for url parameters
            if param == 'url' and param_type == 'string':
                if not isinstance(value, str) or not value.startswith(('http://', 'https://')):
                    return f"Error: Parameter 'url' must be a valid HTTP/HTTPS URL"
        
        return None  # No errors
    
    def _parse_response(self, response: str) -> Dict[str, Any]:
        """
        Parse LLM response into structured format
        
        Expected formats:
        1. Thought/Action/Action Input:
           Thought: <reasoning>
           Action: <tool_name>
           Action Input: {"param": "value"}
        
        2. Final Answer:
           Thought: <reasoning>
           Final Answer: <answer>
        
        Returns the FIRST action found to prevent hallucination
        """
        
        # Check for final answer FIRST
        final_answer_match = re.search(
            r'Final Answer:\s*(.+?)(?:\n(?:Thought:|Action:)|$)',
            response,
            re.DOTALL | re.IGNORECASE
        )
        
        if final_answer_match:
            # Extract thought if present
            thought_match = re.search(r'Thought:\s*(.+?)(?=Final Answer:)', response, re.DOTALL | re.IGNORECASE)
            thought = thought_match.group(1).strip() if thought_match else "I have determined the answer."
            
            final_answer = final_answer_match.group(1).strip()
            
            return {
                'is_final': True,
                'thought': thought,
                'final_answer': final_answer,
                'action': None,
                'action_input': None
            }
        
        # Find the FIRST Thought/Action/Action Input sequence only
        # This prevents the agent from planning multiple steps ahead
        
        # Extract the FIRST thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=\n(?:Action:|Thought:)|$)', response, re.DOTALL | re.IGNORECASE)
        
        if not thought_match:
            thought = "I need to analyze this step by step."
        else:
            thought = thought_match.group(1).strip()
            # Remove any text after the first complete sentence or line break
            if '\n' in thought:
                thought = thought.split('\n')[0].strip()
        
        # Extract the FIRST action after the thought
        # Look for "Action:" that's NOT part of a markdown header (###)
        # and NOT followed by a colon (to avoid "Immediate Action:")
        action_match = re.search(r'(?<!#)\bAction:\s*([a-zA-Z_][a-zA-Z0-9_]+)', response, re.IGNORECASE)
        
        if not action_match:
            # Try fallback patterns for common mistakes
            # Pattern 1: Action: **tool_name**
            action_match = re.search(r'(?<!#)\bAction:\s*\*\*([a-zA-Z_][a-zA-Z0-9_]+)\*\*', response, re.IGNORECASE)
            
            if not action_match:
                # No action found - ask agent to provide one
                return {
                    'is_final': False,
                    'thought': thought,
                    'action': None,
                    'action_input': None,
                    'error': 'No action specified. Please specify which tool to use.'
                }
        
        action = action_match.group(1).strip()
        
        # Validate that the action is a known tool
        if not self.tools.has_tool(action):
            # Try to find a similar tool name (case-insensitive)
            available_tools = list(self.tools.get_tool_names())
            similar_tools = [tool for tool in available_tools
                           if action.lower() in tool.lower()
                           or tool.lower() in action.lower()
                           or action.lower().replace('_', '') == tool.lower().replace('_', '')]
            
            if similar_tools:
                suggestion = f"Did you mean one of these tools: {', '.join(similar_tools)}?"
            else:
                suggestion = f"Available tools: {', '.join(available_tools)}"
            
            return {
                'is_final': False,
                'thought': thought,
                'action': action,
                'action_input': None,
                'error': f'Unknown tool "{action}". {suggestion}'
            }
        
        action = action_match.group(1).strip()
        
        # Extract the FIRST action input (must be valid JSON)
        # Look for JSON object after "Action Input:" - be more flexible
        action_input_patterns = [
            r'Action Input:\s*(\{.*?\})(?:\s|$)',  # Action Input: {json}
            r'Action Input:\s*```json\s*(\{.*?\})\s*```',  # Action Input: ```json {json} ```
            r'Action Input:\s*```\s*(\{.*?\})\s*```',  # Action Input: ``` {json} ```
        ]
        
        action_input = None
        for pattern in action_input_patterns:
            match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
            if match:
                try:
                    action_input = json.loads(match.group(1))
                    break
                except json.JSONDecodeError:
                    continue
        
        # Fallback to the original method if patterns didn't work
        if action_input is None:
            action_input_match = re.search(r'Action Input:\s*', response, re.IGNORECASE)
            if action_input_match:
                json_start = action_input_match.end()
                remaining_text = response[json_start:]
                action_input = self._extract_json_from_text(remaining_text)
        
        if action_input is None:
            action_input = {}
        
        return {
            'is_final': False,
            'thought': thought,
            'action': action,
            'action_input': action_input
        }
    
    def _extract_json_from_text(self, text: str) -> Optional[Dict]:
        """
        Extract the first valid JSON object from text.
        Handles nested braces and multiline JSON.
        """
        text = text.strip()
        
        if not text.startswith('{'):
            return {}
        
        # Find matching closing brace
        brace_count = 0
        for i, char in enumerate(text):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    # Found complete JSON object
                    json_str = text[:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        return {}
        
        # No complete JSON found
        return {}
    
    def _get_system_prompt(self, mode_context: str = "") -> str:
        """Generate system prompt with structured prompts"""
        tools_desc = "\n".join([
            f"- {tool.name}: {tool.description}"
            for tool in self.tools.tools.values()
        ])
        
        # Use the mode context if provided, otherwise use base system
        if mode_context:
            # Mode context may include both format_instructions and tools_description placeholders
            from prompts.system_prompts import REACT_FORMAT_INSTRUCTIONS
            return mode_context.format(
                format_instructions=REACT_FORMAT_INSTRUCTIONS,
                tools_description=tools_desc
            )
        else:
            # Use base system prompt
            from prompts import get_base_system_prompt
            return get_base_system_prompt(tools_desc)
    
    def _check_infinite_loop(self) -> bool:
        """Check if agent is repeating the same actions"""
        if not self.loop_detection_enabled:
            return False
        
        if len(self.history) < 3:
            return False
        
        # Check if last 3 actions are identical
        recent_actions = [
            (step.action, json.dumps(step.action_input, sort_keys=True))
            for step in self.history[-3:]
            if step.action is not None
        ]
        
        if len(recent_actions) >= 3 and len(set(recent_actions)) == 1:
            return True
        
        return False
    
    def _handle_error(self, error: Exception, iteration: int) -> Dict[str, Any]:
        """Handle errors gracefully"""
        error_msg = str(error)
        
        suggestion = None
        if "API" in error_msg or "api" in error_msg.lower():
            suggestion = "Check your API configuration and network connection"
        elif "timeout" in error_msg.lower():
            suggestion = "The request timed out. Try again or check the service availability"
        
        self.display.print_error(error_msg, suggestion)
        
        return {
            'success': False,
            'error': error_msg,
            'steps': self.history
        }
