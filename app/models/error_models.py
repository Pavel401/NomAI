from enum import Enum
from typing import Optional, Any, Dict, List
from pydantic import BaseModel, Field
from datetime import datetime


class ErrorCode(str, Enum):
    """Enumeration of standard error codes"""

    INVALID_INPUT = "INVALID_INPUT"
    MISSING_REQUIRED_FIELD = "MISSING_REQUIRED_FIELD"
    INVALID_IMAGE_FORMAT = "INVALID_IMAGE_FORMAT"
    IMAGE_TOO_LARGE = "IMAGE_TOO_LARGE"
    INVALID_BASE64 = "INVALID_BASE64"

    NO_FOOD_DETECTED = "NO_FOOD_DETECTED"
    ANALYSIS_CONFIDENCE_TOO_LOW = "ANALYSIS_CONFIDENCE_TOO_LOW"
    UNSUPPORTED_FOOD_TYPE = "UNSUPPORTED_FOOD_TYPE"

    GEMINI_API_ERROR = "GEMINI_API_ERROR"
    API_RATE_LIMIT_EXCEEDED = "API_RATE_LIMIT_EXCEEDED"
    EXTERNAL_SERVICE_TIMEOUT = "EXTERNAL_SERVICE_TIMEOUT"
    API_KEY_INVALID = "API_KEY_INVALID"

    INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    MEMORY_ERROR = "MEMORY_ERROR"

    ENV_VARIABLE_MISSING = "ENV_VARIABLE_MISSING"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ErrorDetail(BaseModel):
    """Detailed error information"""

    field: Optional[str] = Field(
        None, description="Field that caused the error (for validation errors)"
    )
    value: Optional[Any] = Field(
        None, description="Invalid value that caused the error"
    )
    constraint: Optional[str] = Field(None, description="Constraint that was violated")
    suggestion: Optional[str] = Field(None, description="Suggested fix for the error")


class ErrorMetadata(BaseModel):
    """Extended metadata for error tracking and debugging"""

    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When the error occurred"
    )
    request_id: Optional[str] = Field(
        None, description="Unique identifier for the request"
    )
    user_id: Optional[str] = Field(None, description="User identifier if available")
    endpoint: Optional[str] = Field(
        None, description="API endpoint that generated the error"
    )
    method: Optional[str] = Field(None, description="HTTP method used")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    ip_address: Optional[str] = Field(None, description="Client IP address")
    execution_time_seconds: Optional[float] = Field(
        None, description="Time taken before error occurred"
    )
    stack_trace: Optional[str] = Field(
        None, description="Stack trace for debugging (dev only)"
    )
    additional_context: Optional[Dict[str, Any]] = Field(
        None, description="Additional context data"
    )


class StandardErrorResponse(BaseModel):
    """Standardized error response model for all API endpoints"""

    success: bool = Field(False, description="Always false for error responses")
    error_code: ErrorCode = Field(..., description="Standardized error code")
    error_type: str = Field(..., description="Human-readable error type")
    message: str = Field(..., description="User-friendly error message")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Detailed error information"
    )
    severity: ErrorSeverity = Field(
        ErrorSeverity.MEDIUM, description="Error severity level"
    )
    status_code: int = Field(..., description="HTTP status code")
    metadata: Optional[ErrorMetadata] = Field(
        None, description="Error metadata for debugging"
    )
    help_url: Optional[str] = Field(None, description="URL to documentation or help")
    retry_after: Optional[int] = Field(
        None, description="Seconds to wait before retrying (for rate limits)"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary format"""
        result = self.dict(exclude_none=True)

        if "metadata" in result and result["metadata"]:
            metadata = result["metadata"]
            if "timestamp" in metadata and metadata["timestamp"]:
                if hasattr(metadata["timestamp"], "isoformat"):
                    metadata["timestamp"] = metadata["timestamp"].isoformat()

        return result

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "success": False,
                "error_code": "INVALID_IMAGE_FORMAT",
                "error_type": "Validation Error",
                "message": "The provided image format is not supported",
                "details": [
                    {
                        "field": "imageData",
                        "constraint": "Must be valid base64 encoded JPEG, PNG, or WebP image",
                        "suggestion": "Please ensure your image is properly encoded in base64 format",
                    }
                ],
                "severity": "MEDIUM",
                "status_code": 400,
                "metadata": {
                    "timestamp": "2024-01-01T12:00:00Z",
                    "request_id": "req_123456",
                    "endpoint": "/nutrition/get",
                    "method": "POST",
                },
                "help_url": "https://docs.api.com/errors#invalid-image-format",
            }
        }


class ValidationErrorResponse(BaseModel):
    """Specialized error response for validation errors"""

    success: bool = Field(False)
    error_code: ErrorCode = Field(ErrorCode.INVALID_INPUT)
    error_type: str = Field("Validation Error")
    message: str = Field("One or more validation errors occurred")
    validation_errors: List[ErrorDetail] = Field(
        ..., description="List of validation errors"
    )
    status_code: int = Field(422)
    metadata: Optional[ErrorMetadata] = Field(None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert validation error response to dictionary format"""
        result = self.dict(exclude_none=True)

        if "metadata" in result and result["metadata"]:
            metadata = result["metadata"]
            if "timestamp" in metadata and metadata["timestamp"]:
                if hasattr(metadata["timestamp"], "isoformat"):
                    metadata["timestamp"] = metadata["timestamp"].isoformat()

        return result


class BusinessLogicErrorResponse(BaseModel):
    """Specialized error response for business logic errors"""

    success: bool = Field(False)
    error_code: ErrorCode = Field(...)
    error_type: str = Field("Business Logic Error")
    message: str = Field(...)
    context: Optional[Dict[str, Any]] = Field(
        None, description="Additional business context"
    )
    status_code: int = Field(400)
    metadata: Optional[ErrorMetadata] = Field(None)

    def to_dict(self) -> Dict[str, Any]:
        """Convert business logic error response to dictionary format"""
        result = self.dict(exclude_none=True)

        if "metadata" in result and result["metadata"]:
            metadata = result["metadata"]
            if "timestamp" in metadata and metadata["timestamp"]:
                if hasattr(metadata["timestamp"], "isoformat"):
                    metadata["timestamp"] = metadata["timestamp"].isoformat()

        return result


ERROR_CODE_STATUS_MAP = {
    ErrorCode.INVALID_INPUT: 400,
    ErrorCode.MISSING_REQUIRED_FIELD: 400,
    ErrorCode.INVALID_IMAGE_FORMAT: 400,
    ErrorCode.INVALID_BASE64: 400,
    ErrorCode.NO_FOOD_DETECTED: 400,
    ErrorCode.UNSUPPORTED_FOOD_TYPE: 400,
    ErrorCode.IMAGE_TOO_LARGE: 413,
    ErrorCode.ANALYSIS_CONFIDENCE_TOO_LOW: 422,
    ErrorCode.API_RATE_LIMIT_EXCEEDED: 429,
    ErrorCode.INTERNAL_SERVER_ERROR: 500,
    ErrorCode.MEMORY_ERROR: 500,
    ErrorCode.DATABASE_ERROR: 500,
    ErrorCode.GEMINI_API_ERROR: 502,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: 502,
    ErrorCode.SERVICE_UNAVAILABLE: 503,
    ErrorCode.CONFIGURATION_ERROR: 503,
    ErrorCode.ENV_VARIABLE_MISSING: 503,
    ErrorCode.API_KEY_INVALID: 503,
}

ERROR_CODE_SEVERITY_MAP = {
    ErrorCode.INVALID_INPUT: ErrorSeverity.LOW,
    ErrorCode.MISSING_REQUIRED_FIELD: ErrorSeverity.LOW,
    ErrorCode.INVALID_IMAGE_FORMAT: ErrorSeverity.LOW,
    ErrorCode.INVALID_BASE64: ErrorSeverity.LOW,
    ErrorCode.IMAGE_TOO_LARGE: ErrorSeverity.MEDIUM,
    ErrorCode.NO_FOOD_DETECTED: ErrorSeverity.LOW,
    ErrorCode.ANALYSIS_CONFIDENCE_TOO_LOW: ErrorSeverity.MEDIUM,
    ErrorCode.UNSUPPORTED_FOOD_TYPE: ErrorSeverity.MEDIUM,
    ErrorCode.GEMINI_API_ERROR: ErrorSeverity.HIGH,
    ErrorCode.API_RATE_LIMIT_EXCEEDED: ErrorSeverity.MEDIUM,
    ErrorCode.EXTERNAL_SERVICE_TIMEOUT: ErrorSeverity.HIGH,
    ErrorCode.API_KEY_INVALID: ErrorSeverity.CRITICAL,
    ErrorCode.INTERNAL_SERVER_ERROR: ErrorSeverity.HIGH,
    ErrorCode.DATABASE_ERROR: ErrorSeverity.HIGH,
    ErrorCode.CONFIGURATION_ERROR: ErrorSeverity.CRITICAL,
    ErrorCode.MEMORY_ERROR: ErrorSeverity.HIGH,
    ErrorCode.ENV_VARIABLE_MISSING: ErrorSeverity.CRITICAL,
    ErrorCode.SERVICE_UNAVAILABLE: ErrorSeverity.HIGH,
}
