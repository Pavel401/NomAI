import time
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.models.NutritionInputPayload import NutritionInputPayload
from app.services.nutrition_service import NutritionService
from app.models.ServiceResponse import NutritionServiceResponse, ErrorResponse
from app.exceptions import BaseNomAIException, ValidationException
from app.utils.error_handler import ErrorHandler
from app.models.ErrorModels import ErrorCode, ErrorDetail

router = APIRouter()


@router.post(
    "/get",
    response_model=NutritionServiceResponse,
    description="Get nutrition information from an image and user input.",
)
def generate_nutrition_info(query: NutritionInputPayload, request: Request):
    """
    Generate nutrition information from an image with comprehensive error handling.

    Args:
        query: The nutrition query containing image data and user preferences
        request: FastAPI request object for error context

    Returns:
        JSONResponse: Structured response with nutrition data or error information
    """
    start_time = time.time()

    try:
        # Validate required fields
        if not query.imageData:
            raise ValidationException(
                message="Image data is required",
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                field="imageData",
                constraint="required",
                suggestion="Please provide a valid base64 encoded image",
            )

        # Extract query parameters
        user_message = query.food_description
        base64_img = query.imageData

        # Call the nutrition service (which handles its own errors internally)
        response = NutritionService.get_nutrition_data(
            base64_img,
            user_message,
            query.selectedGoals,
            query.dietaryPreferences,
            query.allergies,
        )

        # Return the response (could be success or error)
        return JSONResponse(content=response.to_dict(), status_code=response.status)

    except BaseNomAIException as e:
        # Handle our custom exceptions using the error handler
        execution_time = time.time() - start_time
        error_response = ErrorHandler.handle_custom_exception(
            exception=e, request=request, execution_time=execution_time
        )

        return JSONResponse(
            status_code=error_response.status_code, content=error_response.to_dict()
        )

    except Exception as e:
        # Handle any other unexpected exceptions
        execution_time = time.time() - start_time
        error_response = ErrorHandler.handle_unexpected_exception(
            exception=e,
            request=request,
            execution_time=execution_time,
            user_message="An unexpected error occurred while processing your nutrition request",
        )

        return JSONResponse(
            status_code=error_response.status_code, content=error_response.to_dict()
        )


@router.post(
    "/description",
    response_model=NutritionServiceResponse,
    description="Get nutrition information from a description of food items.",
)
def generate_nutrition_info_from_description(
    query: NutritionInputPayload, request: Request
):
    """
    Generate nutrition information from a description of food items with comprehensive error handling.
    Args:
        query: The nutrition query containing description and user preferences
        request: FastAPI request object for error context
    Returns:
        JSONResponse: Structured response with nutrition data or error information
    """
    start_time = time.time()

    try:
        # Validate required fields
        if not query.food_description:
            raise ValidationException(
                message="Food description is required",
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                field="food_description",
                constraint="required",
                suggestion="Please provide a valid description of the food items",
            )

        # Call the nutrition service (which handles its own errors internally)
        response = NutritionService.log_food_nutrition_data_using_description(query)

        # Return the response (could be success or error)
        return JSONResponse(content=response.to_dict(), status_code=response.status)

    except BaseNomAIException as e:
        # Handle our custom exceptions using the error handler
        execution_time = time.time() - start_time
        error_response = ErrorHandler.handle_custom_exception(
            exception=e, request=request, execution_time=execution_time
        )

        return JSONResponse(
            status_code=error_response.status_code, content=error_response.to_dict()
        )

    except Exception as e:
        # Handle any other unexpected exceptions
        execution_time = time.time() - start_time
        error_response = ErrorHandler.handle_unexpected_exception(
            exception=e,
            request=request,
            execution_time=execution_time,
            user_message="An unexpected error occurred while processing your nutrition request",
        )

        return JSONResponse(
            status_code=error_response.status_code, content=error_response.to_dict()
        )
