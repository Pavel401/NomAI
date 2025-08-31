from typing import Optional, Any, Dict, List
from app.models.ErrorModels import ErrorCode, ErrorDetail, ErrorSeverity


class BaseNomAIException(Exception):
    """Base exception class for all NomAI custom exceptions"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        details: Optional[List[ErrorDetail]] = None,
        context: Optional[Dict[str, Any]] = None,
        severity: Optional[ErrorSeverity] = None,
    ):
        self.message = message
        self.error_code = error_code
        self.details = details or []
        self.context = context or {}
        self.severity = severity
        super().__init__(self.message)


class ValidationException(BaseNomAIException):
    """Exception for input validation errors"""

    def __init__(
        self,
        message: str = "Validation failed",
        error_code: ErrorCode = ErrorCode.INVALID_INPUT,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        constraint: Optional[str] = None,
        suggestion: Optional[str] = None,
    ):
        details = []
        if field or value or constraint or suggestion:
            details.append(
                ErrorDetail(
                    field=field,
                    value=value,
                    constraint=constraint,
                    suggestion=suggestion,
                )
            )

        super().__init__(
            message=message,
            error_code=error_code,
            details=details,
            severity=ErrorSeverity.LOW,
        )


class ImageProcessingException(BaseNomAIException):
    """Exception for image processing related errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.INVALID_IMAGE_FORMAT,
        image_size: Optional[int] = None,
        image_format: Optional[str] = None,
    ):
        context = {}
        if image_size:
            context["image_size"] = image_size
        if image_format:
            context["image_format"] = image_format

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            severity=ErrorSeverity.MEDIUM,
        )


class NutritionAnalysisException(BaseNomAIException):
    """Exception for nutrition analysis related errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.NO_FOOD_DETECTED,
        confidence_score: Optional[float] = None,
        detected_objects: Optional[List[str]] = None,
    ):
        context = {}
        if confidence_score is not None:
            context["confidence_score"] = confidence_score
        if detected_objects:
            context["detected_objects"] = detected_objects

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            severity=ErrorSeverity.MEDIUM,
        )


class ExternalServiceException(BaseNomAIException):
    """Exception for external service integration errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.GEMINI_API_ERROR,
        service_name: Optional[str] = None,
        service_response_code: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        context = {}
        if service_name:
            context["service_name"] = service_name
        if service_response_code:
            context["service_response_code"] = service_response_code
        if retry_after:
            context["retry_after"] = retry_after

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            severity=ErrorSeverity.HIGH,
        )


class ConfigurationException(BaseNomAIException):
    """Exception for configuration and environment related errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode = ErrorCode.CONFIGURATION_ERROR,
        config_key: Optional[str] = None,
        expected_type: Optional[str] = None,
    ):
        context = {}
        if config_key:
            context["config_key"] = config_key
        if expected_type:
            context["expected_type"] = expected_type

        super().__init__(
            message=message,
            error_code=error_code,
            context=context,
            severity=ErrorSeverity.CRITICAL,
        )


class RateLimitException(BaseNomAIException):
    """Exception for rate limiting errors"""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: int = 60,
        limit_type: Optional[str] = None,
    ):
        context = {
            "retry_after": retry_after,
            "limit_type": limit_type or "api_requests",
        }

        super().__init__(
            message=message,
            error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED,
            context=context,
            severity=ErrorSeverity.MEDIUM,
        )


class BusinessLogicException(BaseNomAIException):
    """Exception for business logic related errors"""

    def __init__(
        self,
        message: str,
        error_code: ErrorCode,
        business_context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            error_code=error_code,
            context=business_context or {},
            severity=ErrorSeverity.MEDIUM,
        )


def invalid_image_format(
    message: str = "Invalid image format", image_format: Optional[str] = None
) -> ImageProcessingException:
    """Create an invalid image format exception"""
    return ImageProcessingException(
        message=message,
        error_code=ErrorCode.INVALID_IMAGE_FORMAT,
        image_format=image_format,
    )


def image_too_large(
    message: str = "Image file too large", image_size: Optional[int] = None
) -> ImageProcessingException:
    """Create an image too large exception"""
    return ImageProcessingException(
        message=message, error_code=ErrorCode.IMAGE_TOO_LARGE, image_size=image_size
    )


def no_food_detected(
    message: str = "No food detected in the provided image",
) -> NutritionAnalysisException:
    """Create a no food detected exception"""
    return NutritionAnalysisException(
        message=message, error_code=ErrorCode.NO_FOOD_DETECTED
    )


def low_confidence_analysis(
    confidence_score: float, message: str = "Analysis confidence too low"
) -> NutritionAnalysisException:
    """Create a low confidence analysis exception"""
    return NutritionAnalysisException(
        message=message,
        error_code=ErrorCode.ANALYSIS_CONFIDENCE_TOO_LOW,
        confidence_score=confidence_score,
    )


def gemini_api_error(
    message: str = "Gemini API error", service_response_code: Optional[int] = None
) -> ExternalServiceException:
    """Create a Gemini API error exception"""
    return ExternalServiceException(
        message=message,
        error_code=ErrorCode.GEMINI_API_ERROR,
        service_name="Gemini AI",
        service_response_code=service_response_code,
    )


def env_variable_missing(variable_name: str) -> ConfigurationException:
    """Create an environment variable missing exception"""
    return ConfigurationException(
        message=f"Required environment variable '{variable_name}' is not set",
        error_code=ErrorCode.ENV_VARIABLE_MISSING,
        config_key=variable_name,
    )


def api_key_invalid(service_name: str = "API") -> ConfigurationException:
    """Create an API key invalid exception"""
    return ConfigurationException(
        message=f"Invalid or expired API key for {service_name}",
        error_code=ErrorCode.API_KEY_INVALID,
        config_key="api_key",
    )
