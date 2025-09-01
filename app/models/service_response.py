from typing import Optional, Any, Dict, Union
from pydantic import BaseModel, Field

from app.models.nutrition_output_payload import NutritionResponseModel


class ServiceMetadata(BaseModel):
    """Metadata for service execution details"""

    input_token_count: Optional[int] = Field(
        None, description="Number of input tokens used"
    )
    output_token_count: Optional[int] = Field(
        None, description="Number of output tokens generated"
    )
    total_token_count: Optional[int] = Field(None, description="Total tokens used")
    estimated_cost: Optional[float] = Field(None, description="Estimated cost in USD")
    execution_time_seconds: float = Field(..., description="Execution time in seconds")


class NutritionServiceResponse(BaseModel):
    """Standardized response model for nutrition service operations"""

    response: Optional[NutritionResponseModel] = Field(
        None, description="The nutrition analysis response"
    )
    status: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Response message")
    metadata: Optional[ServiceMetadata] = Field(
        None, description="Service execution metadata"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format for JSON serialization"""
        result = self.dict()

        if self.response:
            response_dict = self.response.dict()

            if "portion" in response_dict:
                if hasattr(response_dict["portion"], "value"):
                    response_dict["portion"] = response_dict["portion"].value
                elif isinstance(response_dict["portion"], str):
                    pass

            for ingredient in response_dict.get("ingredients", []):
                if "portion" in ingredient:
                    if hasattr(ingredient["portion"], "value"):
                        ingredient["portion"] = ingredient["portion"].value

            for alternative in response_dict.get("suggestAlternatives", []):
                if "portion" in alternative:
                    if hasattr(alternative["portion"], "value"):
                        alternative["portion"] = alternative["portion"].value

            result["response"] = response_dict

        return result

    def json(self, **kwargs) -> str:
        """Override JSON serialization to handle enums properly"""
        return super().json(by_alias=True, exclude_none=False, **kwargs)

    class Config:
        use_enum_values = (
            True  # This tells Pydantic to use enum values instead of enum objects
        )
        json_schema_extra = {
            "example": {
                "response": {
                    "message": "Analysis completed successfully",
                    "foodName": "Chicken Caesar Salad",
                    "portion": "cup",
                    "portionSize": 2.0,
                    "confidenceScore": 8,
                    "ingredients": [],
                    "primaryConcerns": [],
                    "suggestAlternatives": [],
                    "overallHealthScore": 75,
                    "overallHealthComments": "Balanced meal with good protein content",
                },
                "status": 200,
                "message": "SUCCESS",
                "metadata": {
                    "input_token_count": 1250,
                    "output_token_count": 450,
                    "total_token_count": 1700,
                    "estimated_cost": 0.0034,
                    "execution_time_seconds": 2.45,
                },
            }
        }


class ErrorResponse(BaseModel):
    """Standardized error response model"""

    response: str = Field("", description="Empty response for errors")
    status: int = Field(..., description="HTTP error status code")
    message: str = Field(..., description="Error message")
    metadata: Optional[ServiceMetadata] = Field(
        None, description="Service execution metadata"
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert error response to dictionary format"""
        return self.dict()

    def json(self, **kwargs) -> str:
        """Override JSON serialization"""
        return super().json(by_alias=True, exclude_none=False, **kwargs)

    class Config:
        use_enum_values = True
        json_schema_extra = {
            "example": {
                "response": "",
                "status": 500,
                "message": "Internal server error: Connection timeout",
                "metadata": {"execution_time_seconds": 0.15},
            }
        }
