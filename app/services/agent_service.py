from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai import Agent
from pydantic_ai.usage import UsageLimits

from app.config.chat_config import chat_config

import logfire

from pydantic_ai import Agent, RunContext

from app.models.NutritionInputPayload import NutritionInputPayload
from app.models.ServiceResponse import NutritionServiceResponse
from app.services.nutrition_service import NutritionService

logfire.configure()
logfire.instrument_pydantic_ai()


class AgentService:

    model = OpenAIModel(
        chat_config.model_name,
        provider=OpenAIProvider(api_key=chat_config.openai_api_key),
    )

    @staticmethod
    def calculate_nutrition_by_food_description(
        food_description: str,
        dietary_preferences: list[str] = None,
        allergies: list[str] = None,
        health_goals: list[str] = None,
    ) -> NutritionServiceResponse:
        """
        Calculate nutrition information based on food description.

        Args:
            food_description: Description of the food item (e.g., "grilled chicken breast with rice")
            dietary_preferences: List of dietary preferences (e.g., ["vegetarian", "low-carb"])
            allergies: List of known allergies (e.g., ["nuts", "dairy"])
            health_goals: List of health goals (e.g., ["weight_loss", "muscle_gain"])
        """
        # Create NutritionInputPayload from individual parameters
        nutrition_data = NutritionInputPayload(
            food_description=food_description,
            dietaryPreferences=dietary_preferences or [],
            allergies=allergies or [],
            selectedGoals=health_goals or [],
            imageData=None,  # No image data from chat
        )

        result = NutritionService.log_food_nutrition_data_using_description(
            nutrition_data
        )
        return result

    agent = Agent(
        model=model,
        tools=[calculate_nutrition_by_food_description],
        system_prompt=chat_config.system_prompt,
    )

    @staticmethod
    def create_chat_agent():
        """Create and return a chat agent instance."""
        return AgentService.agent
