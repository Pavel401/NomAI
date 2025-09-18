from dotenv import load_dotenv

from google.genai import types
import base64
import json
import os
import time
from typing import Optional, List, Dict, Any, Union
from google import genai
from dotenv import load_dotenv
from app.models.nutrition_output_payload import NutritionResponseModel
from app.services.image_service import ImageService
from app.services.prompt_service import PromptService
from app.models.nutrition_input_payload import NutritionInputPayload
from app.models.service_response import (
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
from app.models.error_models import ErrorCode
from google.genai import types

load_dotenv()


load_dotenv()


class DietService:
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

            except Exception as e:
                if "authentication" in str(e).lower() or "api key" in str(e).lower():
                    raise api_key_invalid("Google Gemini AI")
                else:
                    raise ConfigurationException(
                        message=f"Failed to initialize Gemini client: {str(e)}",
                        error_code=ErrorCode.CONFIGURATION_ERROR,
                    ) from e

        return cls._client
