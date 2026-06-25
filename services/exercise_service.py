"""
Exercise Recommendation Service
Uses Gradient Boosting to predict intensity level, then maps to
condition-safe exercise templates with modification guidance.
"""
import numpy as np
from typing import List
from loguru import logger

from services.model_loader import ModelLoader
from models.schemas import (
    ExerciseRecommendationRequest, ExerciseRecommendationResponse,
    ExerciseItem, IntensityLevel
)

INTENSITY_MAP = {0: "very_light", 1: "light", 2: "moderate", 3: "vigorous"}

# Exercise templates keyed by [intensity][condition_profile]
EXERCISE_TEMPLATES = {
    "very_light": {
        "warmUp": ExerciseItem(
            exercise="Seated neck and shoulder rolls",
            duration=5, intensity=IntensityLevel.very_light,
            description="Gently roll shoulders backward 5x, then forward 5x. Tilt head side to side.",
            modifications="Can be done lying down if mobility is limited.",
            caloriesBurnedEstimate=10
        ),
        "mainExercise": ExerciseItem(
            exercise="Chair-based range of motion",
            duration=15, intensity=IntensityLevel.very_light,
            description="Seated leg lifts, ankle circles, and gentle arm raises while seated.",
            modifications="Use a sturdy, non-wheeled chair. Skip any movement that causes pain.",
            caloriesBurnedEstimate=35
        ),
        "coolDown": ExerciseItem(
            exercise="Diaphragmatic breathing",
            duration=5, intensity=IntensityLevel.very_light,
            description="Slow belly breathing: inhale 4s, hold 2s, exhale 6s. Repeat 10 times.",
            caloriesBurnedEstimate=5
        )
    },
    "light": {
        "warmUp": ExerciseItem(
            exercise="Slow walking warm-up",
            duration=5, intensity=IntensityLevel.very_light,
            description="Walk at a conversational pace to elevate heart rate gently.",
            caloriesBurnedEstimate=20
        ),
        "mainExercise": ExerciseItem(
            exercise="Brisk walking",
            duration=25, intensity=IntensityLevel.light,
            description="Walk at a pace where you can hold a conversation. Aim for flat terrain.",
            modifications="Use walking poles if balance is an issue. Reduce to 15 min if fatigued.",
            caloriesBurnedEstimate=100
        ),
        "coolDown": ExerciseItem(
            exercise="Static stretching",
            duration=8, intensity=IntensityLevel.very_light,
            description="Hold each stretch for 20–30s: calf, hip flexor, hamstring, shoulder.",
            caloriesBurnedEstimate=15
        )
    },
    "moderate": {
        "warmUp": ExerciseItem(
            exercise="Dynamic warm-up",
            duration=8, intensity=IntensityLevel.light,
            description="Leg swings, arm circles, hip rotations, and high knee marching.",
            caloriesBurnedEstimate=30
        ),
        "mainExercise": ExerciseItem(
            exercise="Cycling or swimming",
            duration=30, intensity=IntensityLevel.moderate,
            description="Stationary bike at 60–70% max HR, or low-impact lap swimming.",
            modifications="Adjust resistance/speed to keep heart rate comfortable.",
            caloriesBurnedEstimate=220
        ),
        "coolDown": ExerciseItem(
            exercise="Yoga cool-down flow",
            duration=10, intensity=IntensityLevel.very_light,
            description="Child's pose → cat-cow → seated forward fold. Hold each 30–45s.",
            caloriesBurnedEstimate=25
        )
    },
    "vigorous": {
        "warmUp": ExerciseItem(
            exercise="RAMP warm-up",
            duration=10, intensity=IntensityLevel.light,
            description="Raise: jumping jacks → Activate: glute bridges → Mobilise: leg swings → Potentiate: squat jumps.",
            caloriesBurnedEstimate=45
        ),
        "mainExercise": ExerciseItem(
            exercise="HIIT circuit",
            duration=25, intensity=IntensityLevel.vigorous,
            description="4 rounds: 40s burpees → 20s rest → 40s mountain climbers → 20s rest → 40s jump squats.",
            modifications="Replace jumps with step-ups if joint issues present.",
            caloriesBurnedEstimate=350
        ),
        "coolDown": ExerciseItem(
            exercise="Full body stretch",
            duration=10, intensity=IntensityLevel.very_light,
            description="Pigeon pose, spinal twist, chest opener, calf stretch. Hold 30s each.",
            caloriesBurnedEstimate=20
        )
    }
}

# Condition-based safety overrides
CONDITION_SAFETY = {
    "cardiac": {
        "max_intensity": "light",
        "safety_notes": [
            "Keep heart rate below 60% of max (220 - age).",
            "Stop immediately if chest pain, dizziness, or shortness of breath occurs.",
            "Always exercise with someone nearby."
        ],
        "avoid": ["HIIT", "vigorous", "burpees", "jump squats"]
    },
    "arthritis": {
        "max_intensity": "moderate",
        "safety_notes": [
            "Avoid high-impact exercises on affected joints.",
            "Warm water exercise (hydrotherapy) is highly beneficial.",
            "Exercise during low-pain periods."
        ],
        "avoid": ["running", "jump", "high-impact"]
    },
    "copd": {
        "max_intensity": "moderate",
        "safety_notes": [
            "Use pursed-lip breathing during exertion.",
            "Rest if oxygen saturation drops below 90%.",
            "Avoid exercising in cold or polluted air."
        ],
        "avoid": ["vigorous", "HIIT"]
    },
    "diabetes": {
        "max_intensity": "vigorous",
        "safety_notes": [
            "Check blood glucose before and after exercise.",
            "Carry fast-acting carbohydrates in case of hypoglycaemia.",
            "Avoid exercise if blood glucose >250 mg/dL with ketones present."
        ],
        "avoid": []
    },
    "osteoporosis": {
        "max_intensity": "moderate",
        "safety_notes": [
            "Focus on weight-bearing and balance exercises.",
            "Avoid forward spinal flexion movements.",
            "Prioritise fall prevention."
        ],
        "avoid": ["high-impact", "burpees"]
    }
}

WEEKLY_GOALS = {
    "very_light": "3–4 sessions per week, 15–20 minutes each. Focus on consistency over intensity.",
    "light": "4–5 sessions per week, 20–30 minutes each. Build to 150 minutes weekly.",
    "moderate": "3–4 sessions per week, 30–45 minutes each. Target 150 minutes moderate activity.",
    "vigorous": "3 sessions per week, 20–30 minutes each. Equivalent to 75 minutes vigorous weekly."
}


def encode_activity(level: str) -> int:
    return {"sedentary": 0, "lightly_active": 1, "moderately_active": 2,
            "very_active": 3, "extremely_active": 4}.get(level, 0)


def average_past_duration(history: list) -> float:
    if not history:
        return 20.0
    durations = [h.duration for h in history if h.duration]
    return np.mean(durations) if durations else 20.0


def build_feature_vector(req: ExerciseRecommendationRequest) -> np.ndarray:
    conditions_lower = [c.lower() for c in req.condition]
    return np.array([[
        req.energyLevel,
        req.painLevel,
        req.age or 40,
        encode_activity(req.activityLevel),
        len(req.condition),
        average_past_duration(req.exerciseHistory),
        int(any("cardiac" in c or "heart" in c for c in conditions_lower)),
        int(any("arthritis" in c for c in conditions_lower)),
    ]])


def get_safe_intensity(req: ExerciseRecommendationRequest, predicted: str) -> str:
    """Apply condition-based intensity cap."""
    intensity_order = ["very_light", "light", "moderate", "vigorous"]
    max_intensity = predicted

    conditions_lower = [c.lower() for c in req.condition]
    for condition, rules in CONDITION_SAFETY.items():
        if any(condition in c for c in conditions_lower):
            cap = rules["max_intensity"]
            if intensity_order.index(cap) < intensity_order.index(max_intensity):
                max_intensity = cap

    # Also cap based on pain and energy
    if req.painLevel >= 7 or req.energyLevel <= 2:
        max_intensity = "very_light"
    elif req.painLevel >= 4 or req.energyLevel <= 4:
        if intensity_order.index(max_intensity) > intensity_order.index("light"):
            max_intensity = "light"

    return max_intensity


def get_safety_notes(req: ExerciseRecommendationRequest) -> List[str]:
    notes = ["Stop exercising if you feel pain, dizziness, or unusual shortness of breath."]
    conditions_lower = [c.lower() for c in req.condition]
    for condition, rules in CONDITION_SAFETY.items():
        if any(condition in c for c in conditions_lower):
            notes.extend(rules["safety_notes"])
    return list(set(notes))  # deduplicate


async def get_exercise_recommendations(req: ExerciseRecommendationRequest) -> ExerciseRecommendationResponse:
    model = ModelLoader.get_exercise_model()

    if model:
        try:
            features = build_feature_vector(req)
            idx = int(model.predict(features)[0])
            predicted = INTENSITY_MAP.get(idx, "light")
        except Exception as e:
            logger.warning(f"Exercise model predict failed: {e}, using rule fallback")
            predicted = _rule_based_intensity(req)
    else:
        predicted = _rule_based_intensity(req)

    intensity = get_safe_intensity(req, predicted)
    logger.info(f"Exercise intensity: predicted={predicted}, safe={intensity}")

    template = EXERCISE_TEMPLATES[intensity]

    return ExerciseRecommendationResponse(
        warmUp=template["warmUp"],
        mainExercise=template["mainExercise"],
        coolDown=template["coolDown"],
        weeklyGoal=WEEKLY_GOALS[intensity],
        safetyNotes=get_safety_notes(req),
        avoidIfSymptoms=["chest pain", "shortness of breath", "severe joint pain", "dizziness", "nausea"]
    )


def _rule_based_intensity(req: ExerciseRecommendationRequest) -> str:
    if req.painLevel >= 6 or req.energyLevel <= 3:
        return "very_light"
    if req.energyLevel <= 5:
        return "light"
    if req.activityLevel in ["very_active", "extremely_active"]:
        return "vigorous"
    return "moderate"
