from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent

from app.config.chat_config import chat_config


def create_chat_agent() -> Agent:
    """Create and configure the chat agent with OpenAI model."""

    # Check if chat is properly configured
    if not chat_config.is_configured():
        raise ValueError(chat_config.get_error_message())

    model = OpenAIModel(
        chat_config.model_name,
        provider=OpenAIProvider(api_key=chat_config.openai_api_key),
    )

    agent = Agent(model=model, system_prompt=chat_config.system_prompt)

    return agent
