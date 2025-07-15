"""
Configuration settings for the chat functionality.
"""

from typing import Optional

from app.config.model_config import ModelCode
from app.utils.envManager import get_env_variable_safe


class ChatConfig:
    """Configuration for chat functionality."""

    def __init__(self):
        self.openai_api_key = self._get_openai_key()
        self.model_name = ModelCode.OPENAI_GPT_4o_MINI.value
        self.max_messages = 100
        self.system_prompt = "You are NomAI, a helpful AI nutrition assistant. You can help with nutrition questions, food analysis, dietary advice, and general health information. Be friendly, informative, and always remind users to consult healthcare professionals for medical advice."
        self.enable_debug = True
        self.database_file = ".chat_app_messages.sqlite"

    def _get_openai_key(self) -> Optional[str]:
        """Get OpenAI API key from environment variables."""
        # Try both possible environment variable names
        api_key = get_env_variable_safe("OPENAI_API_KEY", "")

        return api_key if api_key else None

    def get_error_message(self) -> str:
        """Get error message for missing configuration."""
        if not self.openai_api_key:
            return "OpenAI API key not configured. Please set OPENAI_API_KEY in your environment variables."
        return "Chat functionality is not properly configured."

    def is_configured(self) -> bool:
        """Check if chat functionality is properly configured."""
        return self.openai_api_key is not None and self.openai_api_key != ""


# Global config instance
chat_config = ChatConfig()
