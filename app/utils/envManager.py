import os
from typing import Optional
from dotenv import load_dotenv
from app.exceptions import env_variable_missing


def get_env_variable(key: str, default: Optional[str] = None) -> str:
    """
    Get environment variable with proper error handling.

    Args:
        key: The environment variable key
        default: Default value if key is not found (optional)

    Returns:
        str: The environment variable value

    Raises:
        ConfigurationException: If the key is not found and no default is provided
    """
    load_dotenv()

    value = os.getenv(key, default)

    if value is None:
        raise env_variable_missing(key)

    return value


def get_env_variable_safe(key: str, default: str = "") -> str:
    """
    Safely get environment variable without raising exceptions.

    Args:
        key: The environment variable key
        default: Default value if key is not found

    Returns:
        str: The environment variable value or default
    """
    load_dotenv()
    return os.getenv(key, default)
