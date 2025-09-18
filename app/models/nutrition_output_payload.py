import enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from typing_extensions import (
    Annotated,
)  # for Python <3.9, otherwise use `from typing import Annotated`


class Portion(enum.Enum):
    CUP = "cup"
    GRAM = "gram"
    SLICES = "slices"


class Status(enum.Enum):
    SUCCESS = 200
    ERROR = 400


class NutritionRecommendation(BaseModel):
    """Model for recommended foods to complement nutrition"""

    food: str = Field(..., description="Complementary food to add")
    quantity: str = Field(..., description="Recommended quantity to add")
    reasoning: str = Field(..., description="How this helps balance nutrition")


class PrimaryConcern(BaseModel):
    """Model for primary nutritional concerns identified in the food"""

    issue: str = Field(..., description="Primary nutritional concern")
    explanation: str = Field(..., description="Brief explanation of health impact")
    recommendations: List[NutritionRecommendation] = Field(
        default_factory=list,
        description="List of recommended foods to address the concern",
    )


class NutritionInfo(BaseModel):
    """Detailed nutritional information for a food item"""

    name: str
    calories: int = Field(
        ...,
    )
    protein: int = Field(
        ...,
    )
    carbs: int = Field(
        ...,
    )
    fiber: int = Field(
        ...,
    )  # Fixed spelling from 'fibre' to 'fiber' for consistency
    fat: int = Field(
        ...,
    )
    healthScore: int = Field(
        ...,
    )
    healthComments: str


class NutritionResponseModel(BaseModel):
    """Response model for nutrition analysis"""

    message: Optional[str] = Field(None, description="Status message or error details")
    imageUrl: Optional[str] = Field(None, description="URL of the analyzed food image")
    foodName: str = Field(..., description="Name of the analyzed food")
    portion: Portion = Field(..., description="Portion type")
    portionSize: float = Field(..., description="Size of the portion")
    confidenceScore: int = Field(
        ..., description="Confidence score of the analysis (0-10)"
    )
    ingredients: List[NutritionInfo] = Field(
        default_factory=list, description="Nutritional breakdown of ingredients"
    )
    primaryConcerns: List[PrimaryConcern] = Field(
        default_factory=list,
        description="Primary nutritional concerns and recommendations",
    )
    suggestAlternatives: List[NutritionInfo] = Field(
        default_factory=list, description="Healthier alternative options"
    )
    overallHealthScore: int = Field(..., description="Overall health score from 0-100")
    overallHealthComments: str = Field(
        ..., description="Summary health assessment and recommendations"
    )

    class Config:
        use_enum_values = True  # Serialize enum values instead of enum objects
