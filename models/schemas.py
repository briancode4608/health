from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ActivityLevel(str, Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    extremely_active = "extremely_active"


class IntensityLevel(str, Enum):
    very_light = "very_light"
    light = "light"
    moderate = "moderate"
    vigorous = "vigorous"
    very_vigorous = "very_vigorous"


# ── Meal Recommendation ──────────────────────────────────────────────────────

class MealRecommendationRequest(BaseModel):
    age: Optional[int] = Field(None, ge=1, le=120)
    weight: Optional[float] = Field(None, gt=0, description="kg")
    height: Optional[float] = Field(None, gt=0, description="cm")
    bmi: Optional[float] = None
    conditions: List[str] = Field(default_factory=list)
    activityLevel: ActivityLevel = ActivityLevel.sedentary
    dietaryRestrictions: List[str] = Field(default_factory=list)


class MealItem(BaseModel):
    name: str
    portion: str
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    notes: Optional[str] = None


class NutritionSummary(BaseModel):
    totalCalories: int
    totalProtein: float
    totalCarbs: float
    totalFat: float
    totalFiber: Optional[float] = None
    hydrationGoalLiters: float = 2.0


class MealRecommendationResponse(BaseModel):
    breakfast: List[MealItem]
    lunch: List[MealItem]
    dinner: List[MealItem]
    snacks: List[MealItem] = Field(default_factory=list)
    nutritionSummary: NutritionSummary
    generalAdvice: List[str] = Field(default_factory=list)


# ── Exercise Recommendation ──────────────────────────────────────────────────

class ExerciseHistoryItem(BaseModel):
    exerciseType: str
    duration: int
    intensity: Optional[str] = None
    date: Optional[str] = None


class ExerciseRecommendationRequest(BaseModel):
    condition: List[str] = Field(default_factory=list)
    activityLevel: ActivityLevel = ActivityLevel.sedentary
    age: Optional[int] = Field(None, ge=1, le=120)
    weight: Optional[float] = None
    energyLevel: int = Field(5, ge=1, le=10)
    painLevel: int = Field(0, ge=0, le=10)
    exerciseHistory: List[ExerciseHistoryItem] = Field(default_factory=list)


class ExerciseItem(BaseModel):
    exercise: str
    duration: int  # minutes
    intensity: IntensityLevel
    description: str
    modifications: Optional[str] = None
    caloriesBurnedEstimate: Optional[int] = None


class ExerciseRecommendationResponse(BaseModel):
    warmUp: ExerciseItem
    mainExercise: ExerciseItem
    coolDown: ExerciseItem
    weeklyGoal: str
    safetyNotes: List[str] = Field(default_factory=list)
    avoidIfSymptoms: List[str] = Field(default_factory=list)


# ── Food Scan ────────────────────────────────────────────────────────────────

class FoodNutrition(BaseModel):
    calories: int
    protein: float
    carbs: float
    fat: float
    fiber: Optional[float] = None
    sodium: Optional[float] = None
    sugar: Optional[float] = None


class FoodScanResponse(BaseModel):
    detectedFood: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    alternativeDetections: List[Dict[str, Any]] = Field(default_factory=list)
    estimatedCalories: int
    nutritionData: FoodNutrition
    portionEstimate: str
    healthScore: Optional[int] = Field(None, ge=1, le=10)
    allergenWarnings: List[str] = Field(default_factory=list)


# ── Health Insights ──────────────────────────────────────────────────────────

class SymptomEntry(BaseModel):
    name: str
    severity: int


class HealthLogEntry(BaseModel):
    date: str
    mood: Optional[int] = None
    energyLevel: Optional[int] = None
    sleepHours: Optional[float] = None
    symptoms: List[SymptomEntry] = Field(default_factory=list)
    painLevel: Optional[int] = None
    stressLevel: Optional[int] = None


class MealLogEntry(BaseModel):
    date: str
    mealType: Optional[str] = None
    calories: Optional[int] = None
    nutritionSummary: Optional[Dict] = None


class ExerciseLogEntry(BaseModel):
    date: str
    exerciseType: Optional[str] = None
    duration: Optional[int] = None
    intensity: Optional[str] = None


class UserProfileContext(BaseModel):
    conditions: List[str] = Field(default_factory=list)
    age: Optional[int] = None
    activityLevel: Optional[str] = None


class HealthInsightsRequest(BaseModel):
    userProfile: UserProfileContext
    healthLogs: List[HealthLogEntry] = Field(default_factory=list)
    mealLogs: List[MealLogEntry] = Field(default_factory=list)
    exerciseLogs: List[ExerciseLogEntry] = Field(default_factory=list)


class InsightItem(BaseModel):
    category: str
    title: str
    description: str
    severity: str  # info | warning | alert
    recommendation: str


class HealthInsightsResponse(BaseModel):
    insights: List[InsightItem]
    energyTrend: str
    sleepTrend: str
    symptomPatterns: List[str]
    lifestyleRecommendations: List[str]
    anomaliesDetected: List[str] = Field(default_factory=list)
    overallWellnessScore: Optional[float] = None
