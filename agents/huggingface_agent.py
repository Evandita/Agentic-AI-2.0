"""Hugging Face agent implementation"""

import requests
from typing import List, Dict
from agents.base import BaseAgent
from tools.registry import ToolRegistry
from ui.display import DisplayManager
from config import AgentConfig
from errors import HuggingFaceAPIError


class HuggingFaceAgent(BaseAgent):
    """Agent using Hugging Face Inference API"""

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
            name="Hugging Face API Red Team Agent",
            tool_registry=tool_registry,
            display=display,
            max_iterations=max_iterations,
            logger=logger,
            loop_detection_enabled=loop_detection_enabled
        )

        self.api_key = config.huggingface_api_key
        self.model = config.huggingface_model
        self.config = config
        self.api_url = "https://router.huggingface.co/v1/chat/completions"

    def update_model(self, model_name: str) -> None:
        """Update the model being used by this agent"""
        self.model = model_name

    def _call_llm(self, prompt: str, history: List[Dict]) -> str:
        """
        Call Hugging Face Inference API synchronously
        """
        try:
            # Log the request
            self.step_counter += 1
            if self.logger:
                self.logger.log_llm_prompt(self.step_counter, prompt, self.model)

            # Build messages for chat completions format
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

            # Call Hugging Face Router API with chat completions format
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.model,
                "messages": messages,
                "max_tokens": 512,
                "temperature": 0.3,
                "top_p": 0.9,
                "stream": False
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                raise HuggingFaceAPIError(
                    f"Hugging Face API returned status {response.status_code}: {response.text}"
                )

            result = response.json()

            # Handle chat completions response format
            if isinstance(result, dict) and 'choices' in result:
                choices = result['choices']
                if len(choices) > 0 and 'message' in choices[0]:
                    response_text = choices[0]['message'].get('content', '')
                else:
                    response_text = ''
            # Fallback for old format (in case some models still use it)
            elif isinstance(result, list) and len(result) > 0:
                response_text = result[0].get('generated_text', '')
            elif isinstance(result, dict):
                response_text = result.get('generated_text', '')
            else:
                response_text = str(result)

            if not response_text:
                raise HuggingFaceAPIError("Empty response from Hugging Face API")

            # Log the response
            if self.logger:
                self.logger.log_llm_response(self.step_counter, response_text)

            return response_text

        except requests.exceptions.Timeout:
            raise HuggingFaceAPIError("Request to Hugging Face API timed out")
        except requests.exceptions.RequestException as e:
            raise HuggingFaceAPIError(f"Network error calling Hugging Face API: {str(e)}")
        except Exception as e:
            if "API_KEY" in str(e).upper() or "AUTHORIZATION" in str(e).upper():
                raise HuggingFaceAPIError("Invalid Hugging Face API key. Please check your HUGGINGFACE_API_KEY in .env file")
            raise HuggingFaceAPIError(f"Error calling Hugging Face API: {str(e)}")