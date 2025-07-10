from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from ..constants.chat_config import chat_config
import logfire


def create_chat_agent() -> Agent:
    """Create and configure the chat agent with OpenAI model."""

    # Check if chat is properly configured
    if not chat_config.is_configured():
        raise ValueError(chat_config.get_error_message())

    # Configure logfire
    logfire.configure(send_to_logfire="if-token-present")
    logfire.instrument_pydantic_ai()

    model = OpenAIModel(
        chat_config.model_name,
        provider=OpenAIProvider(api_key=chat_config.openai_api_key),
    )

    agent = Agent(model=model, system_prompt=chat_config.system_prompt)

    return agent
