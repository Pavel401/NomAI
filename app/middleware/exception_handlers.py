import traceback
import uuid
from typing import Union, Dict, Any
from datetime import datetime

import logfire
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.exceptions import (
    BaseNomAIException,
    ValidationException,
    ImageProcessingException,
    NutritionAnalysisException,
    ExternalServiceException,
    ConfigurationException,
    RateLimitException,
    BusinessLogicException,
)
from app.models.ErrorModels import (
    StandardErrorResponse,
    ValidationErrorResponse,
    BusinessLogicErrorResponse,
    ErrorCode,
    ErrorDetail,
    ErrorSeverity,
    ErrorMetadata,
    ERROR_CODE_STATUS_MAP,
    ERROR_CODE_SEVERITY_MAP,
)
from app.utils.envManager import get_env_variable_safe


def create_error_metadata(
    request: Request,
    start_time: datetime,
    request_id: str,
    stack_trace: str = None,
    additional_context: Dict[str, Any] = None,
) -> ErrorMetadata:
    """Create error metadata for tracking and debugging."""
    execution_time = (datetime.utcnow() - start_time).total_seconds()

    is_dev = get_env_variable_safe("PROD", "false").lower() != "true"

    return ErrorMetadata(
        timestamp=datetime.utcnow(),
        request_id=request_id,
        endpoint=str(request.url.path),
        method=request.method,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
        execution_time_seconds=execution_time,
        stack_trace=stack_trace if is_dev else None,
        additional_context=additional_context,
    )


async def nomai_exception_handler(
    request: Request, exc: BaseNomAIException
) -> JSONResponse:
    """Handle all custom NomAI exceptions."""
    request_id = str(uuid.uuid4())
    start_time = getattr(request.state, "start_time", datetime.utcnow())

    status_code = ERROR_CODE_STATUS_MAP.get(exc.error_code, 500)

    severity = exc.severity or ERROR_CODE_SEVERITY_MAP.get(
        exc.error_code, ErrorSeverity.MEDIUM
    )

    metadata = create_error_metadata(
        request=request,
        start_time=start_time,
        request_id=request_id,
        stack_trace=traceback.format_exc(),
        additional_context=exc.context,
    )

    log_data = {
        "error_code": exc.error_code.value,
        "message": exc.message,
        "status_code": status_code,
        "request_id": request_id,
        "endpoint": str(request.url.path),
        "context": exc.context,
    }

    if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
        logfire.error("NomAI Exception", **log_data)
    elif severity == ErrorSeverity.MEDIUM:
        logfire.warn("NomAI Exception", **log_data)
    else:
        logfire.info("NomAI Exception", **log_data)

    if isinstance(exc, ValidationException):
        error_response = ValidationErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            validation_errors=exc.details,
            status_code=status_code,
            metadata=metadata,
        )
    elif isinstance(exc, BusinessLogicException):
        error_response = BusinessLogicErrorResponse(
            error_code=exc.error_code,
            message=exc.message,
            context=exc.context,
            status_code=status_code,
            metadata=metadata,
        )
    else:
        retry_after = None
        if isinstance(exc, RateLimitException):
            retry_after = exc.context.get("retry_after")

        error_response = StandardErrorResponse(
            error_code=exc.error_code,
            error_type=exc.__class__.__name__.replace("Exception", " Error"),
            message=exc.message,
            details=exc.details,
            severity=severity,
            status_code=status_code,
            metadata=metadata,
            retry_after=retry_after,
        )

    return JSONResponse(
        status_code=status_code,
        content=error_response.to_dict(),
    )


async def validation_exception_handler(
    request: Request, exc: Union[RequestValidationError, ValidationError]
) -> JSONResponse:
    """Handle FastAPI validation errors."""
    request_id = str(uuid.uuid4())
    start_time = getattr(request.state, "start_time", datetime.utcnow())

    validation_errors = []
    for error in exc.errors():
        field_path = " -> ".join(str(loc) for loc in error["loc"])
        validation_errors.append(
            ErrorDetail(
                field=field_path,
                value=error.get("input"),
                constraint=error["type"],
                suggestion=error["msg"],
            )
        )

    metadata = create_error_metadata(
        request=request,
        start_time=start_time,
        request_id=request_id,
        additional_context={"raw_errors": exc.errors()},
    )

    logfire.info(
        "Validation Error",
        error_count=len(validation_errors),
        request_id=request_id,
        endpoint=str(request.url.path),
    )

    error_response = ValidationErrorResponse(
        message=f"Validation failed with {len(validation_errors)} error(s)",
        validation_errors=validation_errors,
        metadata=metadata,
    )

    return JSONResponse(
        status_code=422,
        content=error_response.to_dict(),
    )


async def http_exception_handler(
    request: Request, exc: Union[HTTPException, StarletteHTTPException]
) -> JSONResponse:
    """Handle HTTP exceptions."""
    request_id = str(uuid.uuid4())
    start_time = getattr(request.state, "start_time", datetime.utcnow())

    status_to_error_code = {
        400: ErrorCode.INVALID_INPUT,
        401: ErrorCode.API_KEY_INVALID,
        403: ErrorCode.API_KEY_INVALID,
        404: ErrorCode.INVALID_INPUT,
        405: ErrorCode.INVALID_INPUT,
        413: ErrorCode.IMAGE_TOO_LARGE,
        429: ErrorCode.API_RATE_LIMIT_EXCEEDED,
        500: ErrorCode.INTERNAL_SERVER_ERROR,
        502: ErrorCode.EXTERNAL_SERVICE_TIMEOUT,
        503: ErrorCode.SERVICE_UNAVAILABLE,
    }

    error_code = status_to_error_code.get(
        exc.status_code, ErrorCode.INTERNAL_SERVER_ERROR
    )
    severity = ERROR_CODE_SEVERITY_MAP.get(error_code, ErrorSeverity.MEDIUM)

    metadata = create_error_metadata(
        request=request,
        start_time=start_time,
        request_id=request_id,
    )

    logfire.warn(
        "HTTP Exception",
        status_code=exc.status_code,
        message=str(exc.detail),
        request_id=request_id,
        endpoint=str(request.url.path),
    )

    error_response = StandardErrorResponse(
        error_code=error_code,
        error_type="HTTP Error",
        message=str(exc.detail),
        severity=severity,
        status_code=exc.status_code,
        metadata=metadata,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.to_dict(),
    )


async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    request_id = str(uuid.uuid4())
    start_time = getattr(request.state, "start_time", datetime.utcnow())

    metadata = create_error_metadata(
        request=request,
        start_time=start_time,
        request_id=request_id,
        stack_trace=traceback.format_exc(),
        additional_context={"exception_type": exc.__class__.__name__},
    )

    logfire.error(
        "Unexpected Exception",
        exception_type=exc.__class__.__name__,
        message=str(exc),
        request_id=request_id,
        endpoint=str(request.url.path),
        stack_trace=traceback.format_exc(),
    )

    is_dev = get_env_variable_safe("PROD", "false").lower() != "true"
    message = str(exc) if is_dev else "An unexpected error occurred"

    error_response = StandardErrorResponse(
        error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        error_type="Internal Server Error",
        message=message,
        severity=ErrorSeverity.HIGH,
        status_code=500,
        metadata=metadata,
    )

    return JSONResponse(
        status_code=500,
        content=error_response.to_dict(),
    )


def setup_exception_handlers(app: FastAPI) -> FastAPI:
    """Set up global exception handlers for the FastAPI application."""

    app.add_exception_handler(BaseNomAIException, nomai_exception_handler)

    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(ValidationError, validation_exception_handler)

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    app.add_exception_handler(Exception, general_exception_handler)

    logfire.info("Exception handlers configured successfully")

    return app
