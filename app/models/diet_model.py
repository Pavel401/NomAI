from typing import List
from gotrue import Field
from groq import BaseModel
import enum


class DietInput(BaseModel):
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
    )
    fat: int = Field(
        ...,
    )

    dietaryPreferences: List[str] = Field(
        default_factory=list, description="User's dietary preferences"
    )
    allergies: List[str] = Field(
        default_factory=list, description="User's food allergies"
    )
    selectedGoals: List[str] = Field(
        default_factory=list, description="User's health goals"
    )

    dislikedFoods: List[str] = Field(
        default_factory=list, description="Foods the user dislikes"
    )

    anyDiseases: List[str] = Field(
        default_factory=list, description="Any diseases the user has"
    )


# class DietOutput(BaseModel):


class Portion(enum.Enum):
    CUP = "cup"
    GRAM = "gram"
    SLICES = "slices"


class GroceryListItem(BaseModel):
    name: str = Field(..., description="Name of the grocery item")
    quantity: str = Field(..., description="Quantity needed")
    notes: str = Field(..., description="Additional notes or instructions")


class FoodItem(BaseModel):
    name: str = Field(..., description="Name of the food item")
    calories: int = Field(..., description="Calories in the food item")
    protein: int = Field(..., description="Protein content in grams")
    carbs: int = Field(..., description="Carbohydrate content in grams")
    fiber: int = Field(..., description="Fiber content in grams")
    typeOfMeal: str = Field(
        ..., description="Type of meal (breakfast, lunch, dinner, snack)"
    )
    fat: int = Field(..., description="Fat content in grams")
    portion: Portion = Field(..., description="Portion unit of the food item")


class DailyDietOutput(BaseModel):

    breakfast: List[FoodItem] = Field(
        default_factory=list, description="List of breakfast food items"
    )
    lunch: List[FoodItem] = Field(
        default_factory=list, description="List of lunch food items"
    )

    snacks: List[FoodItem] = Field(
        default_factory=list, description="List of snack food items"
    )

    dinner: List[FoodItem] = Field(
        default_factory=list, description="List of dinner food items"
    )

    groceryList: List[GroceryListItem] = Field(
        default_factory=list, description="Grocery list for the day"
    )
    totalCalories: int = Field(..., description="Total calories for the day")

    cheatMealOfTheDay: FoodItem = Field(
        ..., description="Cheat meal suggestion for the day"
    )


class WeeklyDietOutput(BaseModel):
    days: List[DailyDietOutput] = Field(
        default_factory=list, description="List of daily diet outputs for the week"
    )


class SuggestedDifferentMealInput(BaseModel):
    mealPrompt: str = Field(..., description="Prompt describing the meal")
    currentMeal: FoodItem = Field(..., description="Current meal details")
    mealType: str = Field(
        ..., description="Type of meal (breakfast, lunch, dinner, snack)"
    )
    dietaryPreferences: List[str] = Field(
        default_factory=list, description="User's dietary preferences"
    )
    allergies: List[str] = Field(
        default_factory=list, description="User's food allergies"
    )
    dislikedFoods: List[str] = Field(
        default_factory=list, description="Foods the user dislikes"
    )
    anyDiseases: List[str] = Field(
        default_factory=list, description="Any diseases the user has"
    )
    selectedGoals: List[str] = Field(
        default_factory=list, description="User's health goals"
    )
