from fastapi import APIRouter

from app.models.diet_model import DietInput


router = APIRouter()


@router.post("/weeklyDiet")
def generate_weekly_diet(query: DietInput):

    return {"message": "Weekly diet plan generation is not yet implemented."}
