import base64
import json
import os
import time
from typing import Optional, List, Dict, Any, Union
from google import genai
from dotenv import load_dotenv
from app.models.NutritionOutputPayload import NutritionResponseModel
from app.services.image_service import ImageService
from app.services.prompt_service import PromptService
from app.models.NutritionInputPayload import NutritionInputPayload
from app.models.ServiceResponse import (
    NutritionServiceResponse,
    ErrorResponse,
    ServiceMetadata,
)

import requests

from app.utils.token import calculate_cost
from app.exceptions import (
    ExternalServiceException,
    ConfigurationException,
    NutritionAnalysisException,
    BusinessLogicException,
    ValidationException,
    ImageProcessingException,
    gemini_api_error,
    env_variable_missing,
    api_key_invalid,
    no_food_detected,
    low_confidence_analysis,
)
from app.models.ErrorModels import ErrorCode
from google.genai import types

load_dotenv()


class NutritionService:
    """
    Service class for handling nutrition analysis operations.
    Provides methods for analyzing food images and extracting nutritional information.
    """

    _client = None

    @classmethod
    def _get_client(cls) -> genai.Client:
        """Get or create the Gemini client instance with proper error handling."""
        if cls._client is None:
            try:
                api_key = os.getenv("GOOGLE_API_KEY")
                if not api_key:
                    raise env_variable_missing("GOOGLE_API_KEY")

                cls._client = genai.Client(api_key=api_key)

                # Test the client with a simple call if needed
                # This is optional but helps catch authentication issues early

            except Exception as e:
                if "authentication" in str(e).lower() or "api key" in str(e).lower():
                    raise api_key_invalid("Google Gemini AI")
                else:
                    raise ConfigurationException(
                        message=f"Failed to initialize Gemini client: {str(e)}",
                        error_code=ErrorCode.CONFIGURATION_ERROR,
                    ) from e

        return cls._client

    @staticmethod
    def get_nutrition_data(
        query: NutritionInputPayload,
    ) -> NutritionServiceResponse:
        """
        Analyze food image and extract nutritional information using Gemini AI with comprehensive error handling.

        Args:
            base64_img: Base64 encoded image data
            user_message: Optional user message about the food
            selectedGoal: List of user's health goals
            selectedDiet: List of user's dietary preferences
            selectedAllergy: List of user's allergies

        Returns:
            Union[NutritionServiceResponse, ErrorResponse]: Structured response with nutrition data and metadata
        """
        start_time = time.time()

        try:
            # Validate and decode base64 image - ImageService handles its own exceptions
            # image_bytes = ImageService.getImageBytes(base64_img)

            # Generate the complete prompt using PromptService
            try:
                prompt = PromptService.get_nutrition_analysis_prompt_for_image(
                    user_message=query.food_description,
                    selectedGoal=query.selectedGoals,
                    selectedDiet=query.dietaryPreferences,
                    selectedAllergy=query.allergies,
                )
            except Exception as e:
                raise BusinessLogicException(
                    message=f"Failed to generate analysis prompt: {str(e)}",
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                ) from e

            # Get client instance - _get_client handles its own exceptions
            client = NutritionService._get_client()

            image_path = query.imageUrl
            image_bytes = requests.get(image_path).content
            image = types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")

            # Send multimodal input (image + prompt) to Gemini
            try:
                response = client.models.generate_content(
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": NutritionResponseModel,
                        # Keep the temperature low for more deterministic output
                        "temperature": 0,
                    },
                    model="gemini-2.0-flash",
                    contents=[prompt, image],
                )
            except Exception as e:
                error_message = str(e).lower()

                if "rate limit" in error_message or "quota" in error_message:
                    raise ExternalServiceException(
                        message="API rate limit exceeded. Please try again later.",
                        error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED,
                        service_name="Gemini AI",
                        retry_after=60,
                    ) from e
                elif "authentication" in error_message or "api key" in error_message:
                    raise api_key_invalid("Google Gemini AI")
                elif "timeout" in error_message:
                    raise ExternalServiceException(
                        message="Request to Gemini AI timed out. Please try again.",
                        error_code=ErrorCode.EXTERNAL_SERVICE_TIMEOUT,
                        service_name="Gemini AI",
                    ) from e
                else:
                    raise gemini_api_error(
                        message=f"Gemini AI service error: {str(e)}"
                    ) from e

            # Extract token usage metadata safely
            try:
                input_token_count = response.usage_metadata.prompt_token_count  # type: ignore
                output_token_count = response.usage_metadata.candidates_token_count  # type: ignore
                total_token_count = response.usage_metadata.total_token_count  # type: ignore
                total_cost = calculate_cost(input_token_count, output_token_count)
            except Exception as e:
                # If we can't get usage metadata, set defaults
                input_token_count = 0
                output_token_count = 0
                total_token_count = 0
                total_cost = 0.0

            # Get the parsed response from Gemini and validate it
            try:
                nutrition_data = response.parsed

                if not nutrition_data:
                    raise NutritionAnalysisException(
                        message="No nutrition data received from analysis service",
                        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    )

                # Validate the analysis results

                print("Parsed response from Gemini:", nutrition_data)

            except NutritionAnalysisException:
                # Re-raise our custom nutrition analysis exceptions
                raise
            except Exception as e:
                raise NutritionAnalysisException(
                    message=f"Failed to parse nutrition analysis results: {str(e)}",
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                ) from e

            execution_time = time.time() - start_time

            # Create metadata object
            metadata = ServiceMetadata(
                input_token_count=input_token_count,
                output_token_count=output_token_count,
                total_token_count=total_token_count,
                estimated_cost=total_cost,
                execution_time_seconds=round(execution_time, 4),
            )

            # Create and return structured response with the parsed nutrition data
            return NutritionServiceResponse(
                response=nutrition_data,
                status=200,
                message="SUCCESS",
                metadata=metadata,
            )

        except (
            ValidationException,
            ImageProcessingException,
            NutritionAnalysisException,
            ExternalServiceException,
            ConfigurationException,
            BusinessLogicException,
        ) as e:
            # Handle our custom exceptions - they should be handled by the endpoint's error handler
            # Re-raise them so the global exception handler can process them properly
            raise e

        except Exception as e:
            # Handle any other unexpected exceptions
            execution_time = time.time() - start_time
            metadata = ServiceMetadata(execution_time_seconds=round(execution_time, 4))

            return ErrorResponse(
                response="",
                status=500,
                message=f"Internal server error: {str(e)}",
                metadata=metadata,
            )

    @staticmethod
    def log_food_nutrition_data_using_description(
        payload: NutritionInputPayload,
    ) -> NutritionServiceResponse:
        """
        Log food nutrition data using a description with proper error handling.
        This function is a placeholder for future implementation.

        Args:
            payload: NutritionInputPayload containing image data and metadata

        Returns:
            LogNutritionResponse: Response indicating success/failure of logging operation
        """
        start_time = time.time()

        try:

            # Generate the complete prompt using PromptService
            try:
                prompt = PromptService.get_nutrition_analysis_prompt_from_description(
                    user_message=payload.food_description,
                    selectedGoal=payload.selectedGoals,
                    selectedDiet=payload.dietaryPreferences,
                    selectedAllergy=payload.allergies,
                )
            except Exception as e:
                raise BusinessLogicException(
                    message=f"Failed to generate analysis prompt: {str(e)}",
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                ) from e

            # Get client instance - _get_client handles its own exceptions
            client = NutritionService._get_client()

            # Send multimodal input (image + prompt) to Gemini
            try:
                response = client.models.generate_content(
                    config={
                        "response_mime_type": "application/json",
                        "response_schema": NutritionResponseModel,
                        # Keep the temperature low for more deterministic output
                        "temperature": 0,
                    },
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
            except Exception as e:
                error_message = str(e).lower()

                if "rate limit" in error_message or "quota" in error_message:
                    raise ExternalServiceException(
                        message="API rate limit exceeded. Please try again later.",
                        error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED,
                        service_name="Gemini AI",
                        retry_after=60,
                    ) from e
                elif "authentication" in error_message or "api key" in error_message:
                    raise api_key_invalid("Google Gemini AI")
                elif "timeout" in error_message:
                    raise ExternalServiceException(
                        message="Request to Gemini AI timed out. Please try again.",
                        error_code=ErrorCode.EXTERNAL_SERVICE_TIMEOUT,
                        service_name="Gemini AI",
                    ) from e
                else:
                    raise gemini_api_error(
                        message=f"Gemini AI service error: {str(e)}"
                    ) from e

            # Extract token usage metadata safely
            try:
                input_token_count = response.usage_metadata.prompt_token_count  # type: ignore
                output_token_count = response.usage_metadata.candidates_token_count  # type: ignore
                total_token_count = response.usage_metadata.total_token_count  # type: ignore
                total_cost = calculate_cost(input_token_count, output_token_count)
            except Exception as e:
                # If we can't get usage metadata, set defaults
                input_token_count = 0
                output_token_count = 0
                total_token_count = 0
                total_cost = 0.0

            # Get the parsed response from Gemini and validate it
            try:
                nutrition_data = response.parsed

                if not nutrition_data:
                    raise NutritionAnalysisException(
                        message="No nutrition data received from analysis service",
                        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                    )

                # Validate the analysis results

            except NutritionAnalysisException:
                # Re-raise our custom nutrition analysis exceptions
                raise
            except Exception as e:
                raise NutritionAnalysisException(
                    message=f"Failed to parse nutrition analysis results: {str(e)}",
                    error_code=ErrorCode.INTERNAL_SERVER_ERROR,
                ) from e

            execution_time = time.time() - start_time

            # Create metadata object
            metadata = ServiceMetadata(
                input_token_count=input_token_count,
                output_token_count=output_token_count,
                total_token_count=total_token_count,
                estimated_cost=total_cost,
                execution_time_seconds=round(execution_time, 4),
            )

            # Create and return structured response with the parsed nutrition data
            return NutritionServiceResponse(
                response=nutrition_data,
                status=200,
                message="SUCCESS",
                metadata=metadata,
            )

        except (
            ValidationException,
            ImageProcessingException,
            NutritionAnalysisException,
            ExternalServiceException,
            ConfigurationException,
            BusinessLogicException,
        ) as e:
            # Handle our custom exceptions - they should be handled by the endpoint's error handler
            # Re-raise them so the global exception handler can process them properly
            raise e

        except Exception as e:
            # Handle any other unexpected exceptions
            execution_time = time.time() - start_time
            metadata = ServiceMetadata(execution_time_seconds=round(execution_time, 4))

            return ErrorResponse(
                response="",
                status=500,
                message=f"Internal server error: {str(e)}",
                metadata=metadata,
            )
