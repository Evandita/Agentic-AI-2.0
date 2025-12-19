"""Ollama agent implementation"""

import requests
from typing import List, Dict
from agents.base import BaseAgent
from tools.registry import ToolRegistry
from ui.display import DisplayManager
from config import AgentConfig
from errors import OllamaConnectionError


class OllamaAgent(BaseAgent):
    """Agent using local Ollama"""
    
    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        display: DisplayManager,
        max_iterations: int = 10,
        logger = None,
        loop_detection_enabled: bool = True
    ):
        super().__init__(
            name="Ollama Red Team Agent",
            tool_registry=tool_registry,
            display=display,
            max_iterations=max_iterations,
            logger=logger,
            loop_detection_enabled=loop_detection_enabled
        )
        
        self.base_url = config.ollama_base_url
        self.model = config.ollama_model
        self.config = config
    
    def update_model(self, model_name: str) -> None:
        """Update the model being used by this agent"""
        self.model = model_name
    
    def _call_llm(self, prompt: str, history: List[Dict]) -> str:
        """
        Call Ollama API synchronously
        """
        try:
            # Log the request
            self.step_counter += 1
            if self.logger:
                self.logger.log_llm_prompt(self.step_counter, prompt, self.model)
            
            # Build messages for Ollama
            messages = []
            
            # Add conversation history
            for msg in history:
                messages.append({
                    'role': msg['role'],
                    'content': msg['content']
                })
            
            # Add new prompt as user message
            messages.append({
                'role': 'user',
                'content': prompt
            })
            
            # Call Ollama chat API
            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    'model': self.model,
                    'messages': messages,
                    'stream': False,
                    'options': {
                        'temperature': 0.3,  # Lower temperature for more focused responses
                        'num_predict': 512,  # Shorter responses to prevent multi-step planning
                        'top_p': 0.9,
                        'top_k': 40,
                        'repeat_penalty': 1.1,
                        # No stop sequences - let the model complete its response
                        # The base agent will truncate multi-step responses
                    }
                },
                timeout=120  # 2 minutes for local models
            )
            
            if response.status_code != 200:
                raise OllamaConnectionError(
                    f"Ollama returned status {response.status_code}: {response.text}"
                )
            
            result = response.json()
            
            if 'message' not in result or 'content' not in result['message']:
                raise OllamaConnectionError("Invalid response format from Ollama")
            
            response_text = result['message']['content']
            
            # Log the response
            if self.logger:
                self.logger.log_llm_response(self.step_counter, response_text)
            
            return response_text
            
        except requests.exceptions.ConnectionError:
            raise OllamaConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. "
                "Please ensure Ollama is running with: ollama serve"
            )
        except requests.exceptions.Timeout:
            raise OllamaConnectionError(
                f"Ollama request timed out. The model might be too slow or overloaded."
            )
        except requests.exceptions.RequestException as e:
            raise OllamaConnectionError(f"Ollama request failed: {str(e)}")
        except Exception as e:
            raise OllamaConnectionError(f"Unexpected error with Ollama: {str(e)}")
