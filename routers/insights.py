from fastapi import APIRouter, HTTPException
from loguru import logger
from models.schemas import HealthInsightsRequest, HealthInsightsResponse
from services.insights_service import generate_insights

router = APIRouter()


@router.post("/health-insights", response_model=HealthInsightsResponse)
async def health_insights(request: HealthInsightsRequest):
    """
    Analyse multi-modal health data and generate actionable insights.
    Detects symptom patterns, trends in mood/energy/sleep, and anomalies.
    Uses IsolationForest anomaly detection + Pearson correlation analysis.
    """
    try:
        total_records = (
            len(request.healthLogs) +
            len(request.mealLogs) +
            len(request.exerciseLogs)
        )
        logger.info(f"Health insights request: {total_records} total records, "
                    f"conditions={request.userProfile.conditions}")

        if total_records == 0:
            return HealthInsightsResponse(
                insights=[],
                energyTrend="stable",
                sleepTrend="stable",
                symptomPatterns=[],
                lifestyleRecommendations=["Start logging health data to receive personalised insights."],
                anomaliesDetected=[],
                overallWellnessScore=None
            )

        result = await generate_insights(request)
        return result

    except Exception as e:
        logger.error(f"Health insights error: {e}")
        raise HTTPException(status_code=500, detail=f"Insights generation failed: {str(e)}")
