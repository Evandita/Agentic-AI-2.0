"""Logging utilities for Red Teaming AI"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any
from agents.base import AgentStep


class SessionLogger:
    """Logger for agent sessions"""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        
        # Create session log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"session_{timestamp}.log"
        self.json_file = self.log_dir / f"session_{timestamp}.json"
        
        # Setup text logger
        self.logger = logging.getLogger(f"session_{timestamp}")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(self.log_file)
        fh.setLevel(logging.INFO)
        
        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        fh.setFormatter(formatter)
        self.logger.addHandler(fh)
        
        # Session data for JSON export
        self.session_data = {
            'start_time': datetime.now().isoformat(),
            'agent': None,
            'mode': None,
            'interactions': []
        }
        
        self.logger.info("Session started")
    
    def log_agent_selection(self, agent_name: str):
        """Log agent selection"""
        self.logger.info(f"Agent selected: {agent_name}")
        self.session_data['agent'] = agent_name
    
    def log_mode_selection(self, mode_name: str):
        """Log mode selection"""
        self.logger.info(f"Mode selected: {mode_name}")
        self.session_data['mode'] = mode_name
    
    def log_user_input(self, user_input: str):
        """Log user input"""
        self.logger.info(f"User input: {user_input}")
    
    def log_llm_prompt(self, step: int, prompt: str, model: str = ""):
        """Log LLM prompt/request (full, no truncation)"""
        model_info = f" [{model}]" if model else ""
        self.logger.info(f"\n=== LLM REQUEST{model_info} (Step {step}) ===")
        self.logger.info(prompt)
        self.logger.info("=== END REQUEST ===\n")
    
    def log_llm_response(self, step: int, response: str, full_response: str = None):
        """Log LLM response (full, no truncation)"""
        self.logger.info(f"\n=== LLM RESPONSE (Step {step}) ===")
        self.logger.info(response)
        self.logger.info("=== END RESPONSE ===\n")
        
        # Store full response if provided (with full content)
        if full_response and len(full_response) != len(response):
            self.logger.info(f"\n=== FULL LLM RESPONSE (Step {step}) ===")
            self.logger.info(full_response)
            self.logger.info("=== END FULL RESPONSE ===\n")
    
    def log_interaction(
        self,
        objective: str,
        result: Dict[str, Any],
        steps: list[AgentStep]
    ):
        """Log a complete interaction"""
        self.logger.info(f"Objective: {objective}")
        self.logger.info(f"Success: {result.get('success', False)}")
        
        if result.get('success'):
            self.logger.info(f"Result: {result.get('result', 'N/A')}")
        else:
            self.logger.info(f"Error: {result.get('error', 'Unknown error')}")
        
        # Log steps
        for step in steps:
            self.logger.info(f"  Step {step.step_number}:")
            self.logger.info(f"    Thought: {step.thought}")
            if step.action:
                self.logger.info(f"    Action: {step.action}")
                self.logger.info(f"    Input: {step.action_input}")
                self.logger.info(f"    Observation: {step.observation[:200]}...")
        
        # Add to session data
        interaction_data = {
            'timestamp': datetime.now().isoformat(),
            'objective': objective,
            'success': result.get('success', False),
            'result': result.get('result'),
            'error': result.get('error'),
            'steps': [
                {
                    'step_number': step.step_number,
                    'thought': step.thought,
                    'action': step.action,
                    'action_input': step.action_input,
                    'observation': step.observation,
                    'is_final': step.is_final,
                    'final_answer': step.final_answer
                }
                for step in steps
            ]
        }
        self.session_data['interactions'].append(interaction_data)
    
    def log_error(self, error_msg: str):
        """Log an error"""
        self.logger.error(error_msg)
    
    def close(self):
        """Close the session and save JSON"""
        self.session_data['end_time'] = datetime.now().isoformat()
        
        # Save JSON
        with open(self.json_file, 'w') as f:
            json.dump(self.session_data, f, indent=2)
        
        self.logger.info("Session ended")
        self.logger.info(f"Session log saved to: {self.log_file}")
        self.logger.info(f"Session data saved to: {self.json_file}")
        
        # Close handlers
        for handler in self.logger.handlers[:]:
            handler.close()
            self.logger.removeHandler(handler)
