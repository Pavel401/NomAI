from typing import Union
from app.exceptions import BusinessLogicException
from app.models.error_models import ErrorCode


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
        if input_tokens < 0 or output_tokens < 0:
            raise BusinessLogicException(
                message="Token counts cannot be negative",
                error_code=ErrorCode.INVALID_INPUT,
                business_context={
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                },
            )

        input_tokens = float(input_tokens)
        output_tokens = float(output_tokens)

        input_cost_per_million = 0.075  # USD per 1M tokens
        output_cost_per_million = 0.30  # USD per 1M tokens

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
