from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from app.config.chat_config import chat_config
from app.tools.agent_tools import create_agent_tools
import logfire

logfire.configure()
logfire.instrument_pydantic_ai()


class AgentService:
    model = OpenAIModel(
        chat_config.model_name,
        provider=OpenAIProvider(api_key=chat_config.openai_api_key),
    )

    agent = Agent(
        model=model,
        system_prompt=chat_config.system_prompt,
    )

    create_agent_tools(agent)

    @staticmethod
    def create_chat_agent():
        """Create and return a chat agent instance."""
        return AgentService.agent
