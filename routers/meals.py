from fastapi import APIRouter, HTTPException
from loguru import logger
from models.schemas import MealRecommendationRequest, MealRecommendationResponse
from services.meal_service import get_meal_recommendations

router = APIRouter()


@router.post("/recommend-meals", response_model=MealRecommendationResponse)
async def recommend_meals(request: MealRecommendationRequest):
    """
    Generate personalised meal recommendations based on user health profile.
    Uses Random Forest classifier + condition-aware rule engine.
    """
    try:
        logger.info(f"Meal recommendation request: conditions={request.conditions}, "
                    f"activity={request.activityLevel}, restrictions={request.dietaryRestrictions}")
        result = await get_meal_recommendations(request)
        return result
    except Exception as e:
        logger.error(f"Meal recommendation error: {e}")
        raise HTTPException(status_code=500, detail=f"Meal recommendation failed: {str(e)}")
