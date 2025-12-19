"""Configuration management for Red Teaming AI system"""

from dataclasses import dataclass
from typing import Optional
from dotenv import load_dotenv
import os
import sys


@dataclass
class AgentConfig:
    """Configuration for red teaming agents"""
    
    # API Keys
    gemini_api_key: Optional[str]
    
    # Ollama Settings
    ollama_base_url: str
    ollama_model: str
    
    # Display Settings
    console_width: str
    log_level: str
    
    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration and return (is_valid, error_messages)
        """
        errors = []
        
        # Check Gemini API key
        if not self.gemini_api_key or self.gemini_api_key == "your_gemini_api_key_here":
            errors.append("GEMINI_API_KEY not configured")
        
        return (len(errors) == 0, errors)


def load_config() -> AgentConfig:
    """
    Load configuration from .env file with fallback defaults
    """
    # Load .env file (searches in current dir and parent dirs)
    load_dotenv()
    
    config = AgentConfig(
        gemini_api_key=os.getenv("GEMINI_API_KEY"),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
        console_width=os.getenv("CONSOLE_WIDTH", "auto"),
        log_level=os.getenv("LOG_LEVEL", "INFO")
    )
    
    return config


def check_api_availability(config: AgentConfig) -> dict[str, bool]:
    """
    Check which APIs are available and configured
    Returns dict with 'gemini' and 'ollama' availability
    """
    availability = {
        'gemini': False,
        'ollama': False
    }
    
    # Check Gemini
    if config.gemini_api_key and config.gemini_api_key != "your_gemini_api_key_here":
        try:
            import google.generativeai as genai
            genai.configure(api_key=config.gemini_api_key)
            availability['gemini'] = True
        except Exception:
            availability['gemini'] = False
    
    # Check Ollama
    try:
        import requests
        response = requests.get(
            f"{config.ollama_base_url}/api/tags",
            timeout=2
        )
        if response.status_code == 200:
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            # Check if configured model is available
            if any(config.ollama_model in name for name in model_names):
                availability['ollama'] = True
    except Exception:
        availability['ollama'] = False
    
    return availability
