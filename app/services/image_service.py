import base64
import binascii
from typing import Optional
from app.exceptions import (
    ValidationException,
    ImageProcessingException,
    invalid_image_format,
    image_too_large,
)
from app.models.error_models import ErrorCode, ErrorDetail


class ImageService:
    """
    Service class for handling image-related operations with proper error handling.
    """

    MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
    SUPPORTED_FORMATS = ["jpeg", "jpg", "png", "webp"]

    @staticmethod
    def validate_base64_string(base64_string: str) -> None:
        """
        Validate if the provided string is valid base64.

        Args:
            base64_string: The base64 string to validate

        Raises:
            ValidationException: If the string is not valid base64
        """
        if not base64_string:
            raise ValidationException(
                message="Image data cannot be empty",
                error_code=ErrorCode.MISSING_REQUIRED_FIELD,
                field="imageData",
                constraint="required",
                suggestion="Please provide a valid base64 encoded image",
            )

        try:
            decoded = base64.b64decode(base64_string, validate=True)
            if len(decoded) == 0:
                raise ValidationException(
                    message="Image data is empty after decoding",
                    error_code=ErrorCode.INVALID_BASE64,
                    field="imageData",
                    constraint="non_empty_after_decode",
                    suggestion="Please ensure the base64 string contains valid image data",
                )
        except (ValueError, binascii.Error) as e:
            raise ValidationException(
                message="Invalid base64 encoding in image data",
                error_code=ErrorCode.INVALID_BASE64,
                field="imageData",
                constraint="valid_base64",
                suggestion="Please ensure the image is properly encoded in base64 format",
            ) from e

    @staticmethod
    def validate_image_size(image_bytes: bytes) -> None:
        """
        Validate if the image size is within acceptable limits.

        Args:
            image_bytes: The decoded image bytes

        Raises:
            ImageProcessingException: If the image is too large
        """
        image_size = len(image_bytes)

        if image_size > ImageService.MAX_IMAGE_SIZE:
            raise image_too_large(
                message=f"Image size ({image_size / (1024*1024):.2f} MB) exceeds maximum allowed size ({ImageService.MAX_IMAGE_SIZE / (1024*1024):.0f} MB)",
                image_size=image_size,
            )

    @staticmethod
    def detect_image_format(image_bytes: bytes) -> Optional[str]:
        """
        Detect the image format from the image bytes.

        Args:
            image_bytes: The image bytes to analyze

        Returns:
            str: Detected image format or None if unknown
        """
        if image_bytes.startswith(b"\xff\xd8\xff"):
            return "jpeg"
        elif image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png"
        elif image_bytes.startswith(b"RIFF") and b"WEBP" in image_bytes[:12]:
            return "webp"
        elif image_bytes.startswith(b"GIF87a") or image_bytes.startswith(b"GIF89a"):
            return "gif"

        return None

    @staticmethod
    def validate_image_format(image_bytes: bytes) -> str:
        """
        Validate if the image format is supported.

        Args:
            image_bytes: The image bytes to validate

        Returns:
            str: The detected image format

        Raises:
            ImageProcessingException: If the format is not supported
        """
        detected_format = ImageService.detect_image_format(image_bytes)

        if detected_format is None:
            raise invalid_image_format(
                message="Unable to detect image format. Please ensure you're uploading a valid image file.",
                image_format="unknown",
            )

        if detected_format not in ImageService.SUPPORTED_FORMATS:
            raise invalid_image_format(
                message=f"Image format '{detected_format}' is not supported. Supported formats: {', '.join(ImageService.SUPPORTED_FORMATS)}",
                image_format=detected_format,
            )

        return detected_format

    @staticmethod
    def getImageBytes(base64Image: str) -> bytes:
        """
        Convert base64 encoded image string to bytes with comprehensive validation.

        Args:
            base64Image: Base64 encoded image string

        Returns:
            bytes: Decoded image bytes

        Raises:
            ValidationException: If base64 validation fails
            ImageProcessingException: If image validation fails
        """
        ImageService.validate_base64_string(base64Image)

        try:
            image_bytes = base64.b64decode(base64Image)

            ImageService.validate_image_size(image_bytes)

            detected_format = ImageService.validate_image_format(image_bytes)

            return image_bytes

        except (ValidationException, ImageProcessingException):
            raise
        except Exception as e:
            raise ImageProcessingException(
                message=f"Failed to process image: {str(e)}",
                error_code=ErrorCode.INVALID_IMAGE_FORMAT,
            ) from e

    @staticmethod
    def validate_and_get_image_info(base64Image: str) -> dict:
        """
        Validate image and return detailed information about it.

        Args:
            base64Image: Base64 encoded image string

        Returns:
            dict: Image information including size, format, etc.
        """
        image_bytes = ImageService.getImageBytes(base64Image)
        image_format = ImageService.detect_image_format(image_bytes)

        return {
            "size_bytes": len(image_bytes),
            "size_mb": round(len(image_bytes) / (1024 * 1024), 2),
            "format": image_format,
            "is_valid": True,
        }
