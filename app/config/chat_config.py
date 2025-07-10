"""
Configuration settings for the chat functionality.
"""

from typing import Optional
from ..utils.envManager import get_env_variable_safe


class ChatConfig:
    """Configuration for chat functionality."""

    def __init__(self):
        self.openai_api_key = self._get_openai_key()
        self.model_name = get_env_variable_safe("CHAT_MODEL", "gpt-4o")
        self.max_messages = int(get_env_variable_safe("CHAT_MAX_MESSAGES", "100"))
        self.system_prompt = get_env_variable_safe(
            "CHAT_SYSTEM_PROMPT",
            "You are NomAI, a helpful AI nutrition assistant. You can help with nutrition questions, food analysis, dietary advice, and general health information. Be friendly, informative, and always remind users to consult healthcare professionals for medical advice.",
        )
        self.enable_debug = (
            get_env_variable_safe("CHAT_DEBUG", "false").lower() == "true"
        )
        self.database_file = get_env_variable_safe(
            "CHAT_DB_FILE", ".chat_app_messages.sqlite"
        )

    def _get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key from environment variables."""
        # Try both possible environment variable names
        api_key = get_env_variable_safe("OPENAI_API_KEY", "")
        if not api_key:
            api_key = get_env_variable_safe("OpenAI-Key-v2", "")
        return api_key if api_key else None

    def is_configured(self) -> bool:
        """Check if chat functionality is properly configured."""
        return self.openai_api_key is not None

    def get_error_message(self) -> str:
        """Get error message for missing configuration."""
        if not self.openai_api_key:
            return "OpenAI API key not configured. Please set OPENAI_API_KEY in your environment variables."
        return "Chat functionality is not properly configured."


# Global config instance
chat_config = ChatConfig()
