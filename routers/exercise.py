from fastapi import APIRouter, HTTPException
from loguru import logger
from models.schemas import ExerciseRecommendationRequest, ExerciseRecommendationResponse
from services.exercise_service import get_exercise_recommendations

router = APIRouter()


@router.post("/recommend-exercise", response_model=ExerciseRecommendationResponse)
async def recommend_exercise(request: ExerciseRecommendationRequest):
    """
    Generate safe, personalised exercise recommendations.
    Uses Gradient Boosting classifier with condition-based intensity capping.
    """
    try:
        logger.info(f"Exercise recommendation request: conditions={request.condition}, "
                    f"energy={request.energyLevel}, pain={request.painLevel}")
        result = await get_exercise_recommendations(request)
        return result
    except Exception as e:
        logger.error(f"Exercise recommendation error: {e}")
        raise HTTPException(status_code=500, detail=f"Exercise recommendation failed: {str(e)}")
