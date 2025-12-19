"""Custom exceptions for Red Teaming AI system"""


class RedTeamError(Exception):
    """Base exception for red teaming system"""
    pass


class ConfigurationError(RedTeamError):
    """Configuration issues"""
    pass


class LLMError(RedTeamError):
    """LLM API errors"""
    pass


class ToolExecutionError(RedTeamError):
    """Tool execution failures"""
    pass


class OllamaConnectionError(LLMError):
    """Ollama not available"""
    pass


class GeminiAPIError(LLMError):
    """Gemini API errors"""
    pass
