"""Gemini agent implementation"""

import google.generativeai as genai
from typing import List, Dict
from agents.base import BaseAgent
from tools.registry import ToolRegistry
from ui.display import DisplayManager
from config import AgentConfig
from errors import GeminiAPIError


class GeminiAgent(BaseAgent):
    """Agent using Google's Gemini API"""
    
    def __init__(
        self,
        config: AgentConfig,
        tool_registry: ToolRegistry,
        display: DisplayManager
    ):
        super().__init__(
            name="Gemini Red Team Agent",
            tool_registry=tool_registry,
            display=display,
            max_iterations=10
        )
        
        # Configure Gemini
        genai.configure(api_key=config.gemini_api_key)
        
        # Use Gemini 1.5 Flash for speed
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.config = config
    
    def _call_llm(self, prompt: str, history: List[Dict]) -> str:
        """
        Call Gemini API synchronously
        """
        try:
            # Gemini uses a different message format
            # We'll use generate_content with a combined prompt
            
            # Combine history and new prompt
            full_prompt = ""
            
            for msg in history:
                if msg['role'] == 'assistant':
                    full_prompt += f"{msg['content']}\n\n"
            
            full_prompt += prompt
            
            # Generate response
            response = self.model.generate_content(
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Lower for more focused responses
                    max_output_tokens=512,  # Shorter to prevent multi-step planning
                    top_p=0.9,
                    top_k=40,
                    stop_sequences=['\nThought:', '\n\nThought:', 'Observation:']  # Stop at next step
                )
            )
            
            if not response.text:
                raise GeminiAPIError("Empty response from Gemini")
            
            return response.text
            
        except Exception as e:
            if "API_KEY" in str(e).upper():
                raise GeminiAPIError(f"Invalid API key. Please check your GEMINI_API_KEY in .env file")
            elif "quota" in str(e).lower():
                raise GeminiAPIError(f"API quota exceeded. Please check your Gemini API usage")
            else:
                raise GeminiAPIError(f"Gemini API error: {str(e)}")
