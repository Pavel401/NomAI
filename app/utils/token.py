from typing import Union
from app.exceptions import BusinessLogicException
from app.models.ErrorModels import ErrorCode


def calculate_cost(
    input_tokens: Union[int, float], output_tokens: Union[int, float]
) -> float:
    """
    Calculate the cost of API usage based on input and output tokens with error handling.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated

    Returns:
        float: Total cost in USD

    Raises:
        BusinessLogicException: If token counts are invalid
    """
    try:
        # Validate inputs
        if input_tokens < 0 or output_tokens < 0:
            raise BusinessLogicException(
                message="Token counts cannot be negative",
                error_code=ErrorCode.INVALID_INPUT,
                business_context={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )

        # Convert to float if necessary
        input_tokens = float(input_tokens)
        output_tokens = float(output_tokens)

        # Pricing constants (as of current Gemini pricing)
        input_cost_per_million = 0.075  # USD per 1M tokens
        output_cost_per_million = 0.30  # USD per 1M tokens

        # Calculate costs
        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million

        total_cost = input_cost + output_cost
        return round(total_cost, 6)  # Rounded for precision

    except ValueError as e:
        raise BusinessLogicException(
            message=f"Invalid token count format: {str(e)}",
            error_code=ErrorCode.INVALID_INPUT,
            business_context={
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
        ) from e
    except Exception as e:
        raise BusinessLogicException(
            message=f"Failed to calculate token cost: {str(e)}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        ) from e


def get_pricing_info() -> dict:
    """
    Get current pricing information for the API.

    Returns:
        dict: Pricing information
    """
    return {
        "input_cost_per_million_tokens": 0.075,
        "output_cost_per_million_tokens": 0.30,
        "currency": "USD",
        "last_updated": "2024-01-01",  # Update this when pricing changes
    }


def estimate_cost_for_request(
    estimated_input_tokens: int, estimated_output_tokens: int
) -> dict:
    """
    Estimate the cost for a request before making it.

    Args:
        estimated_input_tokens: Estimated number of input tokens
        estimated_output_tokens: Estimated number of output tokens

    Returns:
        dict: Cost estimation details
    """
    try:
        total_cost = calculate_cost(estimated_input_tokens, estimated_output_tokens)

        return {
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "estimated_total_tokens": estimated_input_tokens + estimated_output_tokens,
            "estimated_cost_usd": total_cost,
            "cost_breakdown": {
                "input_cost": round((estimated_input_tokens / 1_000_000) * 0.075, 6),
                "output_cost": round((estimated_output_tokens / 1_000_000) * 0.30, 6),
            },
        }
    except Exception as e:
        raise BusinessLogicException(
            message=f"Failed to estimate cost: {str(e)}",
            error_code=ErrorCode.INTERNAL_SERVER_ERROR,
        ) from e
