"""
AI Microservice Tests
Tests for meal recommendation, exercise recommendation,
food scanning, and health insights endpoints.
Run with: pytest tests/test_ai_service.py -v
"""
import pytest
import asyncio
import numpy as np
from httpx import AsyncClient
from unittest.mock import patch, MagicMock

# Import services directly for unit tests
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import (
    MealRecommendationRequest, ExerciseRecommendationRequest,
    HealthInsightsRequest, UserProfileContext, HealthLogEntry,
    ExerciseLogEntry, MealLogEntry, SymptomEntry
)
from services.meal_service import (
    get_meal_recommendations, filter_meals_for_restrictions,
    _rule_based_category, build_feature_vector
)
from services.exercise_service import (
    get_exercise_recommendations, get_safe_intensity,
    _rule_based_intensity, get_safety_notes
)
from services.insights_service import (
    generate_insights, _linear_trend, _detect_anomalies,
    _symptom_patterns, _compute_wellness_score
)
from services.model_loader import ModelLoader


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def load_models():
    """Load ML models once for the test session."""
    await ModelLoader.initialize()
    yield


@pytest.fixture
def diabetic_user_request():
    return MealRecommendationRequest(
        age=52,
        weight=85,
        height=170,
        conditions=["diabetes type 2", "hypertension"],
        activityLevel="lightly_active",
        dietaryRestrictions=["low-sugar"]
    )


@pytest.fixture
def vegan_user_request():
    return MealRecommendationRequest(
        age=28,
        weight=65,
        height=168,
        conditions=[],
        activityLevel="moderately_active",
        dietaryRestrictions=["vegan"]
    )


@pytest.fixture
def cardiac_exercise_request():
    return ExerciseRecommendationRequest(
        condition=["cardiac disease"],
        activityLevel="sedentary",
        age=65,
        weight=80,
        energyLevel=5,
        painLevel=2,
        exerciseHistory=[]
    )


@pytest.fixture
def sample_health_logs():
    return [
        HealthLogEntry(
            date="2024-01-01T08:00:00",
            mood=7, energyLevel=6, sleepHours=7.5,
            symptoms=[SymptomEntry(name="fatigue", severity=3)],
            painLevel=2, stressLevel=4
        ),
        HealthLogEntry(
            date="2024-01-02T08:00:00",
            mood=5, energyLevel=4, sleepHours=5.5,
            symptoms=[SymptomEntry(name="fatigue", severity=5), SymptomEntry(name="headache", severity=4)],
            painLevel=4, stressLevel=6
        ),
        HealthLogEntry(
            date="2024-01-03T08:00:00",
            mood=6, energyLevel=7, sleepHours=8.0,
            symptoms=[SymptomEntry(name="fatigue", severity=2)],
            painLevel=1, stressLevel=3
        ),
        HealthLogEntry(
            date="2024-01-04T08:00:00",
            mood=8, energyLevel=8, sleepHours=8.5,
            symptoms=[],
            painLevel=0, stressLevel=2
        ),
        HealthLogEntry(
            date="2024-01-05T08:00:00",
            mood=4, energyLevel=3, sleepHours=4.5,
            symptoms=[SymptomEntry(name="fatigue", severity=7), SymptomEntry(name="headache", severity=6)],
            painLevel=5, stressLevel=8
        ),
    ]


# ── Meal Service Unit Tests ───────────────────────────────────────────────────

class TestMealService:

    def test_rule_based_category_high_cal_active_lean(self):
        req = MealRecommendationRequest(
            bmi=22.0, activityLevel="very_active"
        )
        assert _rule_based_category(req) == "high_cal"

    def test_rule_based_category_low_cal_obese(self):
        req = MealRecommendationRequest(bmi=33.0, activityLevel="sedentary")
        assert _rule_based_category(req) == "low_cal"

    def test_rule_based_category_medium_default(self):
        req = MealRecommendationRequest(bmi=24.0, activityLevel="lightly_active")
        assert _rule_based_category(req) == "medium_cal"

    def test_feature_vector_shape(self, diabetic_user_request):
        vec = build_feature_vector(diabetic_user_request)
        assert vec.shape == (1, 9)

    def test_diabetic_flag_in_feature_vector(self, diabetic_user_request):
        vec = build_feature_vector(diabetic_user_request)
        assert vec[0, 4] == 1  # is_diabetic flag

    def test_hypertension_flag_in_feature_vector(self, diabetic_user_request):
        vec = build_feature_vector(diabetic_user_request)
        assert vec[0, 5] == 1  # is_hypertensive flag

    @pytest.mark.asyncio
    async def test_meal_recommendations_structure(self, diabetic_user_request):
        result = await get_meal_recommendations(diabetic_user_request)
        assert len(result.breakfast) > 0
        assert len(result.lunch) > 0
        assert len(result.dinner) > 0
        assert result.nutritionSummary.totalCalories > 0
        assert len(result.generalAdvice) > 0

    @pytest.mark.asyncio
    async def test_diabetic_recommendations_exclude_high_sugar(self, diabetic_user_request):
        result = await get_meal_recommendations(diabetic_user_request)
        all_meal_names = (
            [m.name.lower() for m in result.breakfast] +
            [m.name.lower() for m in result.lunch] +
            [m.name.lower() for m in result.dinner]
        )
        # Honey and maple syrup should not appear for diabetics
        for name in all_meal_names:
            assert "honey" not in name, f"Diabetic user got honey in: {name}"
            assert "maple syrup" not in name

    @pytest.mark.asyncio
    async def test_vegan_recommendations_exclude_meat(self, vegan_user_request):
        result = await get_meal_recommendations(vegan_user_request)
        all_meal_names = (
            [m.name.lower() for m in result.breakfast] +
            [m.name.lower() for m in result.lunch] +
            [m.name.lower() for m in result.dinner]
        )
        meat_keywords = ["chicken", "salmon", "fish", "steak", "turkey", "tuna"]
        for name in all_meal_names:
            for keyword in meat_keywords:
                assert keyword not in name, f"Vegan user got {keyword} in meal: {name}"

    @pytest.mark.asyncio
    async def test_meal_advice_for_diabetics(self, diabetic_user_request):
        result = await get_meal_recommendations(diabetic_user_request)
        advice_text = " ".join(result.generalAdvice).lower()
        assert any(kw in advice_text for kw in ["glycaemic", "carbohydrate", "carbs", "blood"])

    @pytest.mark.asyncio
    async def test_nutrition_summary_positive_values(self, vegan_user_request):
        result = await get_meal_recommendations(vegan_user_request)
        s = result.nutritionSummary
        assert s.totalCalories > 0
        assert s.totalProtein >= 0
        assert s.totalCarbs >= 0
        assert s.totalFat >= 0
        assert s.hydrationGoalLiters > 0


# ── Exercise Service Unit Tests ───────────────────────────────────────────────

class TestExerciseService:

    def test_rule_based_intensity_high_pain(self):
        req = ExerciseRecommendationRequest(painLevel=8, energyLevel=5)
        assert _rule_based_intensity(req) == "very_light"

    def test_rule_based_intensity_low_energy(self):
        req = ExerciseRecommendationRequest(painLevel=1, energyLevel=2)
        assert _rule_based_intensity(req) == "very_light"

    def test_rule_based_intensity_vigorous(self):
        req = ExerciseRecommendationRequest(
            painLevel=0, energyLevel=9,
            activityLevel="very_active"
        )
        assert _rule_based_intensity(req) == "vigorous"

    def test_cardiac_patient_capped_at_light(self, cardiac_exercise_request):
        predicted = "moderate"
        result = get_safe_intensity(cardiac_exercise_request, predicted)
        assert result == "light"

    def test_high_pain_overrides_to_very_light(self):
        req = ExerciseRecommendationRequest(
            condition=[], painLevel=8, energyLevel=7,
            activityLevel="very_active"
        )
        result = get_safe_intensity(req, "vigorous")
        assert result == "very_light"

    def test_safety_notes_for_cardiac(self, cardiac_exercise_request):
        notes = get_safety_notes(cardiac_exercise_request)
        assert len(notes) > 1
        notes_text = " ".join(notes).lower()
        assert any(kw in notes_text for kw in ["heart rate", "chest", "stop"])

    @pytest.mark.asyncio
    async def test_exercise_recommendation_structure(self, cardiac_exercise_request):
        result = await get_exercise_recommendations(cardiac_exercise_request)
        assert result.warmUp is not None
        assert result.mainExercise is not None
        assert result.coolDown is not None
        assert result.warmUp.duration > 0
        assert result.mainExercise.duration > 0
        assert len(result.safetyNotes) > 0
        assert len(result.avoidIfSymptoms) > 0

    @pytest.mark.asyncio
    async def test_cardiac_exercise_is_safe_intensity(self, cardiac_exercise_request):
        result = await get_exercise_recommendations(cardiac_exercise_request)
        safe_levels = {"very_light", "light"}
        assert result.mainExercise.intensity.value in safe_levels

    @pytest.mark.asyncio
    async def test_weekly_goal_is_set(self):
        req = ExerciseRecommendationRequest(
            condition=[], energyLevel=7, painLevel=1,
            activityLevel="moderately_active"
        )
        result = await get_exercise_recommendations(req)
        assert result.weeklyGoal
        assert len(result.weeklyGoal) > 10


# ── Insights Service Unit Tests ───────────────────────────────────────────────

class TestInsightsService:

    def test_linear_trend_improving(self):
        values = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
        assert _linear_trend(values) == "improving"

    def test_linear_trend_declining(self):
        values = [8.0, 7.0, 6.0, 5.0, 4.0, 3.0]
        assert _linear_trend(values) == "declining"

    def test_linear_trend_stable(self):
        values = [5.0, 5.1, 4.9, 5.0, 5.1, 5.0]
        assert _linear_trend(values) == "stable"

    def test_linear_trend_too_few_points(self):
        assert _linear_trend([5.0, 6.0]) == "stable"

    def test_anomaly_detection_finds_outlier(self):
        values = [5.0, 5.1, 4.9, 5.0, 5.2, 5.0, 5.1, 1.0]  # 1.0 is outlier
        anomalies = _detect_anomalies(values, threshold=2.0)
        assert len(anomalies) > 0
        assert 7 in anomalies  # index of the outlier

    def test_anomaly_detection_no_anomaly(self):
        values = [5.0, 5.1, 5.2, 4.9, 5.0, 5.1, 5.0, 5.1]
        anomalies = _detect_anomalies(values)
        assert len(anomalies) == 0

    def test_symptom_patterns_finds_frequent(self, sample_health_logs):
        patterns, top_symptoms = _symptom_patterns(sample_health_logs)
        assert "fatigue" in top_symptoms
        # fatigue appears in 4/5 logs
        assert any("fatigue" in p.lower() for p in patterns)

    def test_symptom_cooccurrence(self, sample_health_logs):
        patterns, _ = _symptom_patterns(sample_health_logs)
        # fatigue + headache co-occur in logs 2 and 5
        cooccurrence_found = any(
            "fatigue" in p.lower() and "headache" in p.lower()
            for p in patterns
        )
        assert cooccurrence_found

    def test_wellness_score_range(self, sample_health_logs):
        score = _compute_wellness_score(sample_health_logs)
        assert score is not None
        assert 0 <= score <= 10

    def test_wellness_score_none_for_empty(self):
        score = _compute_wellness_score([])
        assert score is None

    @pytest.mark.asyncio
    async def test_insights_response_structure(self, sample_health_logs):
        req = HealthInsightsRequest(
            userProfile=UserProfileContext(
                conditions=["diabetes type 2"],
                age=52,
                activityLevel="lightly_active"
            ),
            healthLogs=sample_health_logs,
            mealLogs=[],
            exerciseLogs=[]
        )
        result = await generate_insights(req)

        assert hasattr(result, 'insights')
        assert hasattr(result, 'energyTrend')
        assert hasattr(result, 'sleepTrend')
        assert hasattr(result, 'symptomPatterns')
        assert hasattr(result, 'lifestyleRecommendations')
        assert result.energyTrend in {"improving", "declining", "stable"}

    @pytest.mark.asyncio
    async def test_insights_detects_low_sleep(self):
        poor_sleep_logs = [
            HealthLogEntry(
                date=f"2024-01-0{i+1}T08:00:00",
                mood=5, energyLevel=4, sleepHours=4.5
            )
            for i in range(6)
        ]
        req = HealthInsightsRequest(
            userProfile=UserProfileContext(conditions=[]),
            healthLogs=poor_sleep_logs
        )
        result = await generate_insights(req)
        categories = [ins.category for ins in result.insights]
        assert "Sleep" in categories

    @pytest.mark.asyncio
    async def test_insights_no_logs_returns_gracefully(self):
        req = HealthInsightsRequest(
            userProfile=UserProfileContext(conditions=[]),
            healthLogs=[], mealLogs=[], exerciseLogs=[]
        )
        result = await generate_insights(req)
        assert len(result.lifestyleRecommendations) > 0

    @pytest.mark.asyncio
    async def test_insights_detects_declining_mood(self):
        declining_logs = [
            HealthLogEntry(
                date=f"2024-01-{str(i+1).zfill(2)}T08:00:00",
                mood=10 - i, energyLevel=6, sleepHours=7
            )
            for i in range(7)
        ]
        req = HealthInsightsRequest(
            userProfile=UserProfileContext(conditions=[]),
            healthLogs=declining_logs
        )
        result = await generate_insights(req)
        mental_health_insights = [
            ins for ins in result.insights if ins.category == "Mental Health"
        ]
        assert len(mental_health_insights) > 0


# ── Model Loader Tests ────────────────────────────────────────────────────────

class TestModelLoader:

    def test_models_are_loaded(self):
        assert ModelLoader.is_ready()

    def test_meal_model_is_not_none(self):
        assert ModelLoader.get_meal_model() is not None

    def test_exercise_model_is_not_none(self):
        assert ModelLoader.get_exercise_model() is not None

    def test_food_classifier_is_not_none(self):
        clf, le, scaler = ModelLoader.get_food_classifier()
        assert clf is not None
        assert le is not None
        assert scaler is not None

    def test_meal_model_can_predict(self):
        model = ModelLoader.get_meal_model()
        test_input = np.array([[40, 25.0, 2, 1, 0, 0, 0, 0, 0]])
        pred = model.predict(test_input)
        assert pred[0] in [0, 1, 2]

    def test_exercise_model_can_predict(self):
        model = ModelLoader.get_exercise_model()
        test_input = np.array([[6, 2, 40, 2, 1, 25, 0, 0]])
        pred = model.predict(test_input)
        assert pred[0] in [0, 1, 2, 3]

    def test_food_classifier_can_predict_proba(self):
        clf, le, scaler = ModelLoader.get_food_classifier()
        test_features = np.random.randn(1, 64)
        scaled = scaler.transform(test_features)
        proba = clf.predict_proba(scaled)
        assert proba.shape[0] == 1
        assert abs(proba[0].sum() - 1.0) < 1e-5  # probabilities sum to 1
