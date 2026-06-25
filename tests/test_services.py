"""
Tests for AI microservice endpoints and ML logic.
Run with: pytest tests/ -v
"""
import pytest
import asyncio
from unittest.mock import patch, MagicMock
import numpy as np

# ── Schema / Model Tests ──────────────────────────────────────────────────────

def test_meal_request_schema():
    from models.schemas import MealRecommendationRequest, ActivityLevel
    req = MealRecommendationRequest(
        age=45,
        weight=80.0,
        height=170.0,
        conditions=["diabetes"],
        activityLevel=ActivityLevel.lightly_active,
        dietaryRestrictions=["gluten-free"]
    )
    assert req.age == 45
    assert req.conditions == ["diabetes"]
    assert req.activityLevel == "lightly_active"


def test_exercise_request_schema():
    from models.schemas import ExerciseRecommendationRequest
    req = ExerciseRecommendationRequest(
        condition=["arthritis"],
        energyLevel=4,
        painLevel=6
    )
    assert req.energyLevel == 4
    assert req.painLevel == 6


def test_health_insights_request_schema():
    from models.schemas import HealthInsightsRequest, UserProfileContext, HealthLogEntry
    req = HealthInsightsRequest(
        userProfile=UserProfileContext(conditions=["diabetes"], age=50),
        healthLogs=[
            HealthLogEntry(date="2024-01-01", mood=6, energyLevel=5, sleepHours=7.0)
        ]
    )
    assert len(req.healthLogs) == 1
    assert req.userProfile.conditions == ["diabetes"]


# ── Meal Service Tests ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_meal_recommendation_low_cal():
    from services.meal_service import get_meal_recommendations, _rule_based_category
    from models.schemas import MealRecommendationRequest

    req = MealRecommendationRequest(
        age=50, weight=95, height=165, bmi=34.9,
        conditions=[], activityLevel="sedentary", dietaryRestrictions=[]
    )
    # High BMI → low_cal
    category = _rule_based_category(req)
    assert category == "low_cal"


@pytest.mark.asyncio
async def test_meal_recommendation_vegan_filter():
    from services.meal_service import filter_meals_for_restrictions
    from models.schemas import MealItem

    meals = [
        MealItem(name="Grilled Chicken Salad", portion="200g", calories=280, protein=32, carbs=10, fat=9),
        MealItem(name="Lentil Soup", portion="300ml", calories=220, protein=14, carbs=30, fat=3),
    ]
    filtered = filter_meals_for_restrictions(meals, [], ["vegan"])
    names = [m.name for m in filtered]
    assert "Grilled Chicken Salad" not in names
    assert "Lentil Soup" in names


@pytest.mark.asyncio
async def test_meal_recommendation_diabetes_filter():
    from services.meal_service import filter_meals_for_restrictions
    from models.schemas import MealItem

    meals = [
        MealItem(name="Pancakes with Honey and Banana", portion="3 pancakes", calories=400, protein=10, carbs=70, fat=8),
        MealItem(name="Greek Yogurt with Berries", portion="200g", calories=180, protein=15, carbs=20, fat=2),
    ]
    filtered = filter_meals_for_restrictions(meals, ["diabetes"], [])
    names = [m.name for m in filtered]
    # honey should be filtered out
    assert not any("honey" in n.lower() for n in names)


@pytest.mark.asyncio
async def test_meal_full_recommendation_returns_structure():
    from services.meal_service import get_meal_recommendations
    from models.schemas import MealRecommendationRequest

    with patch('services.meal_service.ModelLoader') as mock_loader:
        mock_loader.get_meal_model.return_value = None  # Force rule-based fallback

        req = MealRecommendationRequest(
            age=35, weight=70, height=175,
            conditions=["hypertension"],
            activityLevel="moderately_active",
            dietaryRestrictions=["vegetarian"]
        )
        result = await get_meal_recommendations(req)

    assert len(result.breakfast) > 0
    assert len(result.lunch) > 0
    assert len(result.dinner) > 0
    assert result.nutritionSummary.totalCalories > 0
    assert len(result.generalAdvice) > 0


# ── Exercise Service Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_exercise_cardiac_intensity_cap():
    from services.exercise_service import get_safe_intensity
    from models.schemas import ExerciseRecommendationRequest

    req = ExerciseRecommendationRequest(
        condition=["heart disease"],
        energyLevel=8,
        painLevel=1,
        activityLevel="very_active"
    )
    safe = get_safe_intensity(req, "vigorous")
    assert safe == "light"  # cardiac condition caps at light


@pytest.mark.asyncio
async def test_exercise_high_pain_capped():
    from services.exercise_service import get_safe_intensity
    from models.schemas import ExerciseRecommendationRequest

    req = ExerciseRecommendationRequest(
        condition=[],
        energyLevel=8,
        painLevel=8,  # high pain
    )
    safe = get_safe_intensity(req, "vigorous")
    assert safe == "very_light"


@pytest.mark.asyncio
async def test_exercise_returns_full_structure():
    from services.exercise_service import get_exercise_recommendations
    from models.schemas import ExerciseRecommendationRequest

    with patch('services.exercise_service.ModelLoader') as mock_loader:
        mock_loader.get_exercise_model.return_value = None

        req = ExerciseRecommendationRequest(
            condition=["arthritis"],
            energyLevel=5,
            painLevel=4,
            activityLevel="lightly_active",
            age=60
        )
        result = await get_exercise_recommendations(req)

    assert result.warmUp is not None
    assert result.mainExercise is not None
    assert result.coolDown is not None
    assert len(result.safetyNotes) > 0
    assert result.weeklyGoal


# ── Insights Service Tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_insights_empty_data():
    from services.insights_service import generate_insights
    from models.schemas import HealthInsightsRequest, UserProfileContext

    req = HealthInsightsRequest(
        userProfile=UserProfileContext(conditions=[]),
        healthLogs=[], mealLogs=[], exerciseLogs=[]
    )
    # Should not raise, returns empty insights
    result = await generate_insights(req)
    assert isinstance(result.insights, list)
    assert isinstance(result.symptomPatterns, list)


@pytest.mark.asyncio
async def test_insights_trend_detection():
    from services.insights_service import _linear_trend
    assert _linear_trend([3, 2, 2, 1, 1]) == "declining"
    assert _linear_trend([4, 5, 6, 7, 8]) == "improving"
    assert _linear_trend([5, 5, 5, 5, 5]) == "stable"


@pytest.mark.asyncio
async def test_insights_anomaly_detection():
    from services.insights_service import _detect_anomalies
    values = [5, 5, 5, 5, 1, 5, 5, 5]  # index 4 is anomalous
    anomalies = _detect_anomalies(values)
    assert 4 in anomalies


@pytest.mark.asyncio
async def test_insights_symptom_patterns():
    from services.insights_service import _symptom_patterns
    from models.schemas import HealthLogEntry, SymptomEntry

    logs = [
        HealthLogEntry(date="2024-01-01", symptoms=[
            SymptomEntry(name="fatigue", severity=5),
            SymptomEntry(name="headache", severity=4)
        ]),
        HealthLogEntry(date="2024-01-02", symptoms=[
            SymptomEntry(name="fatigue", severity=6),
            SymptomEntry(name="headache", severity=3)
        ]),
        HealthLogEntry(date="2024-01-03", symptoms=[
            SymptomEntry(name="fatigue", severity=7)
        ]),
    ]
    patterns, top = _symptom_patterns(logs)
    assert "fatigue" in top
    assert any("fatigue" in p.lower() for p in patterns)
    assert any("fatigue" in p.lower() and "headache" in p.lower() for p in patterns)


@pytest.mark.asyncio
async def test_insights_wellness_score():
    from services.insights_service import _compute_wellness_score
    from models.schemas import HealthLogEntry

    logs = [
        HealthLogEntry(date=f"2024-01-0{i+1}", mood=7, energyLevel=7,
                       sleepHours=8.0, painLevel=2, stressLevel=3)
        for i in range(5)
    ]
    score = _compute_wellness_score(logs)
    assert score is not None
    assert 0 <= score <= 10


# ── Food Service Tests ────────────────────────────────────────────────────────

def test_color_heuristic_green():
    from services.food_service import _color_heuristic
    import numpy as np
    # Create a predominantly green image
    img = np.zeros((224, 224, 3), dtype=np.uint8)
    img[:, :] = [50, 180, 50]  # BGR green
    label, conf = _color_heuristic(img)
    assert label == "salad"
    assert 0 < conf <= 1


def test_nutrition_db_completeness():
    from services.food_service import NUTRITION_DB
    required_keys = ["calories", "protein", "carbs", "fat"]
    for food, data in NUTRITION_DB.items():
        for key in required_keys:
            assert key in data, f"Missing '{key}' in NUTRITION_DB['{food}']"


def test_feature_extraction_shape():
    """Verify feature vector is always 64 dims."""
    import numpy as np
    from services.food_service import extract_color_histogram, extract_texture_features
    import cv2
    img = np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)
    color_feats = extract_color_histogram(img)
    texture_feats = extract_texture_features(img)
    combined = np.concatenate([color_feats[:56], texture_feats])
    assert combined.shape == (64,)


# ── Model Loader Tests ────────────────────────────────────────────────────────

def test_meal_model_trains_and_predicts():
    from services.model_loader import ModelLoader
    model = ModelLoader._train_meal_model()
    assert model is not None
    # Test prediction shape
    features = np.array([[35, 24.0, 2, 1, 0, 0, 0, 0, 0]])
    pred = model.predict(features)
    assert pred[0] in [0, 1, 2]


def test_exercise_model_trains_and_predicts():
    from services.model_loader import ModelLoader
    model = ModelLoader._train_exercise_model()
    assert model is not None
    features = np.array([[7, 2, 40, 2, 1, 30.0, 0, 0]])
    pred = model.predict(features)
    assert pred[0] in [0, 1, 2, 3]
