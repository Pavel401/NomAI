from pydantic_ai import Agent, RunContext
from app.models.nutrition_input_payload import NutritionInputPayload
from app.models.service_response import NutritionServiceResponse
from app.services.nutrition_service import NutritionService


def create_agent_tools(agent: Agent, user_context=None):
    """Create and register tools with the provided agent."""

    @agent.tool
    def calculate_nutrition_by_food_description(
        ctx: RunContext,
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
        # Use user context if available and tool parameters are not provided
        if user_context:
            dietary_preferences = (
                dietary_preferences or user_context.dietary_preferences
            )
            allergies = allergies or user_context.allergies
            health_goals = health_goals or user_context.selected_goals

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

    @agent.tool
    def calculate_nutrition_by_image(
        ctx: RunContext,
        query: NutritionInputPayload,
    ) -> NutritionServiceResponse:
        """
        Calculate nutrition information based on image data.

        Args:
            query: NutritionInputPayload containing image URL and other parameters
        """

        result = NutritionService.get_nutrition_data(query=query)
        return result

    return [
        calculate_nutrition_by_food_description,
        calculate_nutrition_by_image,
    ]
