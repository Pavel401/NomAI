import uuid
import traceback
from typing import Optional, Dict, Any, List
from fastapi import Request
from datetime import datetime

from app.models.ErrorModels import (
    StandardErrorResponse,
    ValidationErrorResponse,
    BusinessLogicErrorResponse,
    ErrorCode,
    ErrorDetail,
    ErrorMetadata,
    ErrorSeverity,
    ERROR_CODE_STATUS_MAP,
    ERROR_CODE_SEVERITY_MAP,
)
from app.exceptions import BaseNomAIException
from app.utils.envManager import get_env_variable


class ErrorHandler:
    """Centralized error handling utility"""

    @staticmethod
    def create_error_metadata(
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
        include_stack_trace: bool = False,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> ErrorMetadata:
        """Create error metadata from request and context"""

        request_id = str(uuid.uuid4())
        metadata = ErrorMetadata(
            timestamp=datetime.utcnow(),
            request_id=request_id,
            execution_time_seconds=execution_time,
            additional_context=additional_context,
        )

        if request:
            metadata.endpoint = str(request.url.path)
            metadata.method = request.method
            metadata.user_agent = request.headers.get("user-agent")
            metadata.ip_address = request.client.host if request.client else None

        if include_stack_trace:
            try:
                is_dev = get_env_variable("PROD").lower() != "true"
                if is_dev:
                    metadata.stack_trace = traceback.format_exc()
            except:
                pass

        return metadata

    @staticmethod
    def create_standard_error_response(
        error_code: ErrorCode,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
        additional_context: Optional[Dict[str, Any]] = None,
        help_url: Optional[str] = None,
        retry_after: Optional[int] = None,
    ) -> StandardErrorResponse:
        """Create a standardized error response"""

        status_code = ERROR_CODE_STATUS_MAP.get(error_code, 500)
        severity = ERROR_CODE_SEVERITY_MAP.get(error_code, ErrorSeverity.MEDIUM)

        metadata = ErrorHandler.create_error_metadata(
            request=request,
            execution_time=execution_time,
            include_stack_trace=True,
            additional_context=additional_context,
        )

        return StandardErrorResponse(
            error_code=error_code,
            error_type=ErrorHandler._get_error_type_from_code(error_code),
            message=message,
            details=details,
            severity=severity,
            status_code=status_code,
            metadata=metadata,
            help_url=help_url,
            retry_after=retry_after,
        )

    @staticmethod
    def create_validation_error_response(
        validation_errors: List[ErrorDetail],
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
    ) -> ValidationErrorResponse:
        """Create a validation error response"""

        metadata = ErrorHandler.create_error_metadata(
            request=request, execution_time=execution_time
        )

        return ValidationErrorResponse(
            validation_errors=validation_errors, metadata=metadata
        )

    @staticmethod
    def create_business_logic_error_response(
        error_code: ErrorCode,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
    ) -> BusinessLogicErrorResponse:
        """Create a business logic error response"""

        status_code = ERROR_CODE_STATUS_MAP.get(error_code, 400)

        metadata = ErrorHandler.create_error_metadata(
            request=request, execution_time=execution_time, additional_context=context
        )

        return BusinessLogicErrorResponse(
            error_code=error_code,
            message=message,
            context=context,
            status_code=status_code,
            metadata=metadata,
        )

    @staticmethod
    def handle_custom_exception(
        exception: BaseNomAIException,
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
    ) -> StandardErrorResponse:
        """Handle custom NomAI exceptions"""

        additional_context = exception.context.copy() if exception.context else {}
        additional_context["exception_type"] = type(exception).__name__

        return ErrorHandler.create_standard_error_response(
            error_code=exception.error_code,
            message=exception.message,
            details=exception.details,
            request=request,
            execution_time=execution_time,
            additional_context=additional_context,
        )

    @staticmethod
    def handle_unexpected_exception(
        exception: Exception,
        request: Optional[Request] = None,
        execution_time: Optional[float] = None,
        user_message: str = "An unexpected error occurred",
    ) -> StandardErrorResponse:
        """Handle unexpected exceptions"""

        additional_context = {
            "exception_type": type(exception).__name__,
            "exception_message": str(exception),
        }

        return ErrorHandler.create_standard_error_response(
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
            message=user_message,
            request=request,
            execution_time=execution_time,
            additional_context=additional_context,
        )

    @staticmethod
    def handle_validation_exception(
        exception: Exception, request: Optional[Request] = None
    ) -> ValidationErrorResponse:
        """Handle Pydantic validation exceptions"""

        validation_errors = []

        if hasattr(exception, "errors"):
            for error in exception.errors():
                field_path = ".".join(str(loc) for loc in error.get("loc", []))
                validation_errors.append(
                    ErrorDetail(
                        field=field_path,
                        value=error.get("input"),
                        constraint=error.get("type"),
                        suggestion=f"Please check the {field_path} field: {error.get('msg', '')}",
                    )
                )
        else:
            validation_errors.append(
                ErrorDetail(constraint="validation_failed", suggestion=str(exception))
            )

        return ErrorHandler.create_validation_error_response(
            validation_errors=validation_errors, request=request
        )

    @staticmethod
    def _get_error_type_from_code(error_code: ErrorCode) -> str:
        """Get human-readable error type from error code"""

        error_type_map = {
            ErrorCode.INVALID_INPUT: "Validation Error",
            ErrorCode.MISSING_REQUIRED_FIELD: "Validation Error",
            ErrorCode.INVALID_IMAGE_FORMAT: "Image Processing Error",
            ErrorCode.IMAGE_TOO_LARGE: "Image Processing Error",
            ErrorCode.INVALID_BASE64: "Image Processing Error",
            ErrorCode.NO_FOOD_DETECTED: "Analysis Error",
            ErrorCode.ANALYSIS_CONFIDENCE_TOO_LOW: "Analysis Error",
            ErrorCode.UNSUPPORTED_FOOD_TYPE: "Analysis Error",
            ErrorCode.GEMINI_API_ERROR: "External Service Error",
            ErrorCode.API_RATE_LIMIT_EXCEEDED: "Rate Limit Error",
            ErrorCode.EXTERNAL_SERVICE_TIMEOUT: "External Service Error",
            ErrorCode.API_KEY_INVALID: "Authentication Error",
            ErrorCode.INTERNAL_SERVER_ERROR: "Internal Server Error",
            ErrorCode.DATABASE_ERROR: "Database Error",
            ErrorCode.CONFIGURATION_ERROR: "Configuration Error",
            ErrorCode.MEMORY_ERROR: "System Error",
            ErrorCode.ENV_VARIABLE_MISSING: "Configuration Error",
            ErrorCode.SERVICE_UNAVAILABLE: "Service Unavailable",
        }

        return error_type_map.get(error_code, "Unknown Error")

    @staticmethod
    def get_help_url(error_code: ErrorCode) -> Optional[str]:
        """Get help URL for specific error codes"""

        help_urls = {
            ErrorCode.INVALID_IMAGE_FORMAT: "/docs/errors#invalid-image-format",
            ErrorCode.IMAGE_TOO_LARGE: "/docs/errors#image-too-large",
            ErrorCode.NO_FOOD_DETECTED: "/docs/errors#no-food-detected",
            ErrorCode.API_RATE_LIMIT_EXCEEDED: "/docs/errors#rate-limits",
            ErrorCode.API_KEY_INVALID: "/docs/errors#authentication",
        }

        return help_urls.get(error_code)


def create_image_validation_error(
    message: str, field: str = "imageData"
) -> ValidationErrorResponse:
    """Create an image validation error response"""
    return ErrorHandler.create_validation_error_response(
        [ErrorDetail(field=field, constraint="image_validation", suggestion=message)]
    )


def create_missing_field_error(field_name: str) -> ValidationErrorResponse:
    """Create a missing required field error response"""
    return ErrorHandler.create_validation_error_response(
        [
            ErrorDetail(
                field=field_name,
                constraint="required",
                suggestion=f"The field '{field_name}' is required and cannot be empty",
            )
        ]
    )


def create_rate_limit_error(retry_after: int = 60) -> StandardErrorResponse:
    """Create a rate limit error response"""
    return ErrorHandler.create_standard_error_response(
        error_code=ErrorCode.API_RATE_LIMIT_EXCEEDED,
        message="Too many requests. Please try again later.",
        retry_after=retry_after,
    )
