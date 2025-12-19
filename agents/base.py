"""Base agent implementation with ReAct loop"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import re
import json
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
        logger: Optional[Any] = None
    ):
        self.name = name
        self.tools = tool_registry
        self.display = display
        self.max_iterations = max_iterations
        self.history: List[AgentStep] = []
        self.logger = logger
        self.step_counter = 0
    
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
        
        self.history = []
        conversation_history = []
        
        for iteration in range(self.max_iterations):
            try:
                # Build prompt for this iteration
                if iteration == 0:
                    prompt = f"{system_prompt}\n\nObjective: {objective}\n\nLet's solve this step by step."
                else:
                    # Add previous observation with format reminder
                    if len(self.history) > 0:
                        last_step = self.history[-1]
                        prompt = f"Observation: {last_step.observation}\n\nWhat's your next step? Use the format:\nThought: [reasoning]\nAction: [tool_name]\nAction Input: {{\"param\": \"value\"}}\n\nOr if you have the answer:\nThought: [reasoning]\nFinal Answer: [answer]"
                    else:
                        # No history yet, re-prompt with objective
                        prompt = f"Objective: {objective}\n\nYou MUST use this format:\nThought: [reasoning]\nAction: [tool_name]\nAction Input: {{\"param\": \"value\"}}"
                
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
                    
                    self.display.print_error(
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
                    self.display.print_thinking(parsed['thought'], iteration + 1)
                    self.display.print_final_answer(parsed['final_answer'])
                    
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
                    
                    return {
                        'success': True,
                        'result': parsed['final_answer'],
                        'steps': self.history
                    }
                
                # Display thought
                self.display.print_thinking(parsed['thought'], iteration + 1)
                
                # Execute action
                action_name = parsed['action']
                action_input = parsed['action_input']
                
                self.display.print_tool_call(action_name, action_input, iteration + 1)
                
                # Execute tool
                observation = self._execute_tool(action_name, action_input)
                
                self.display.print_tool_response(action_name, observation, iteration + 1)
                
                # Record step
                step = AgentStep(
                    thought=parsed['thought'],
                    action=action_name,
                    action_input=action_input,
                    observation=observation,
                    step_number=iteration + 1
                )
                self.history.append(step)
                
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
        """Execute tool synchronously"""
        try:
            if not self.tools.has_tool(tool_name):
                return f"Error: Unknown tool '{tool_name}'. Available tools: {', '.join(self.tools.get_tool_names())}"
            
            result = self.tools.execute(tool_name, **tool_input)
            return str(result)
            
        except TypeError as e:
            return f"Error: Invalid parameters for {tool_name}. {str(e)}"
        except Exception as e:
            return f"Error executing {tool_name}: {str(e)}"
    
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
        action_match = re.search(r'Action:\s*(\w+)', response, re.IGNORECASE)
        
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
        
        # Extract the FIRST action input (must be valid JSON)
        # Look for JSON object after "Action Input:"
        action_input_match = re.search(
            r'Action Input:\s*',
            response,
            re.IGNORECASE
        )
        
        if action_input_match:
            # Start from after "Action Input:"
            json_start = action_input_match.end()
            remaining_text = response[json_start:]
            
            # Try to find JSON object
            action_input = self._extract_json_from_text(remaining_text)
            
            if action_input is None:
                # Could not parse JSON
                return {
                    'is_final': False,
                    'thought': thought,
                    'action': action,
                    'action_input': {},
                    'error': f'Could not parse Action Input as valid JSON'
                }
        else:
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
