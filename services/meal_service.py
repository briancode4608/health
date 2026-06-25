"""
Meal Recommendation Service
Uses a Random Forest classifier to determine calorie category,
then applies condition-aware rule engine to select meal templates.
"""
import numpy as np
from typing import List, Dict, Any
from loguru import logger

from services.model_loader import ModelLoader
from models.schemas import (
    MealRecommendationRequest, MealRecommendationResponse,
    MealItem, NutritionSummary
)

# ── Meal Template Database ───────────────────────────────────────────────────
# Each entry: name, portion, calories, protein(g), carbs(g), fat(g), fiber(g)

MEAL_DB = {
    "low_cal": {
        "breakfast": [
            MealItem(name="Greek yogurt with berries", portion="200g + 80g berries",
                     calories=180, protein=15, carbs=20, fat=2, fiber=3),
            MealItem(name="Veggie egg white omelette", portion="3 egg whites + vegetables",
                     calories=160, protein=18, carbs=8, fat=3, fiber=2),
            MealItem(name="Overnight oats (small)", portion="40g oats + almond milk",
                     calories=200, protein=8, carbs=32, fat=5, fiber=5),
        ],
        "lunch": [
            MealItem(name="Grilled chicken salad", portion="150g chicken + mixed greens",
                     calories=280, protein=32, carbs=10, fat=9, fiber=4),
            MealItem(name="Lentil soup", portion="300ml",
                     calories=220, protein=14, carbs=30, fat=3, fiber=8),
            MealItem(name="Tuna with cucumber", portion="120g tuna + cucumber",
                     calories=200, protein=28, carbs=5, fat=4, fiber=2),
        ],
        "dinner": [
            MealItem(name="Steamed fish with broccoli", portion="150g fish + 150g broccoli",
                     calories=260, protein=30, carbs=12, fat=6, fiber=5),
            MealItem(name="Turkey stir-fry with cauliflower rice", portion="200g",
                     calories=290, protein=28, carbs=15, fat=7, fiber=6),
        ],
        "snacks": [
            MealItem(name="Apple slices with almond butter", portion="1 apple + 1 tbsp",
                     calories=150, protein=4, carbs=22, fat=7, fiber=4),
        ]
    },
    "medium_cal": {
        "breakfast": [
            MealItem(name="Oatmeal with banana and honey", portion="80g oats + 1 banana",
                     calories=380, protein=12, carbs=70, fat=6, fiber=8),
            MealItem(name="Whole grain toast with avocado + egg", portion="2 slices + 1/2 avocado + 2 eggs",
                     calories=450, protein=20, carbs=38, fat=24, fiber=7),
            MealItem(name="Smoothie bowl", portion="300ml",
                     calories=340, protein=14, carbs=55, fat=8, fiber=6),
        ],
        "lunch": [
            MealItem(name="Brown rice with grilled salmon", portion="150g rice + 150g salmon",
                     calories=480, protein=36, carbs=50, fat=12, fiber=3),
            MealItem(name="Quinoa veggie bowl", portion="200g quinoa + roasted veg",
                     calories=420, protein=18, carbs=60, fat=10, fiber=9),
            MealItem(name="Chicken wrap with whole wheat tortilla", portion="1 large wrap",
                     calories=460, protein=34, carbs=45, fat=14, fiber=5),
        ],
        "dinner": [
            MealItem(name="Baked chicken breast with sweet potato", portion="180g chicken + 150g potato",
                     calories=450, protein=38, carbs=45, fat=8, fiber=5),
            MealItem(name="Lentil and vegetable curry with rice", portion="350ml curry + 150g rice",
                     calories=490, protein=20, carbs=80, fat=8, fiber=12),
        ],
        "snacks": [
            MealItem(name="Mixed nuts and dried fruit", portion="30g",
                     calories=180, protein=5, carbs=18, fat=11, fiber=2),
            MealItem(name="Hummus with veggie sticks", portion="50g hummus + 100g veg",
                     calories=140, protein=6, carbs=15, fat=7, fiber=4),
        ]
    },
    "high_cal": {
        "breakfast": [
            MealItem(name="Protein pancakes with maple syrup", portion="3 pancakes",
                     calories=580, protein=32, carbs=65, fat=18, fiber=4),
            MealItem(name="Full English with whole grain bread", portion="standard plate",
                     calories=650, protein=38, carbs=45, fat=32, fiber=5),
        ],
        "lunch": [
            MealItem(name="Pasta with meatballs and tomato sauce", portion="300g",
                     calories=620, protein=35, carbs=75, fat=18, fiber=6),
            MealItem(name="Buddha bowl with tahini dressing", portion="large bowl",
                     calories=580, protein=22, carbs=70, fat=22, fiber=12),
        ],
        "dinner": [
            MealItem(name="Grilled steak with roasted potatoes", portion="200g steak + 200g potatoes",
                     calories=680, protein=52, carbs=50, fat=24, fiber=4),
            MealItem(name="Salmon with quinoa and greens", portion="200g salmon + 200g quinoa",
                     calories=600, protein=48, carbs=55, fat=18, fiber=7),
        ],
        "snacks": [
            MealItem(name="Peanut butter banana smoothie", portion="400ml",
                     calories=320, protein=12, carbs=45, fat=12, fiber=4),
        ]
    }
}

# Condition-specific meal filters / replacements
CONDITION_OVERRIDES = {
    "diabetes": {
        "avoid_keywords": ["honey", "maple syrup", "dried fruit", "banana"],
        "prefer": ["lentil", "quinoa", "oats", "vegetables"],
        "advice": "Prioritize low-glycaemic foods; spread carbohydrates evenly across meals."
    },
    "hypertension": {
        "avoid_keywords": ["salt", "sodium"],
        "prefer": ["potassium-rich", "leafy greens", "oats"],
        "advice": "Limit sodium to <2g/day; follow DASH diet principles."
    },
    "celiac": {
        "avoid_keywords": ["bread", "pasta", "pancakes", "tortilla", "wrap"],
        "prefer": ["rice", "quinoa", "oats"],
        "advice": "All grains must be certified gluten-free."
    },
    "heart_disease": {
        "avoid_keywords": ["steak", "full english", "meatballs"],
        "prefer": ["salmon", "oats", "nuts", "berries"],
        "advice": "Favour omega-3 rich foods; limit saturated fat to <10% of calories."
    },
    "kidney_disease": {
        "avoid_keywords": ["banana", "potato", "tomato"],
        "prefer": ["egg whites", "cauliflower", "apple"],
        "advice": "Monitor potassium and phosphorus intake closely."
    }
}

DIETARY_RESTRICTION_FILTERS = {
    "vegan": ["chicken", "fish", "steak", "egg", "salmon", "turkey", "tuna", "yogurt", "meatballs"],
    "vegetarian": ["chicken", "fish", "steak", "salmon", "turkey", "tuna", "meatballs"],
    "gluten-free": ["bread", "pasta", "pancakes", "tortilla", "wrap"],
    "dairy-free": ["yogurt"],
    "low-sodium": [],  # handled separately
}


def encode_activity(level: str) -> int:
    mapping = {"sedentary": 0, "lightly_active": 1, "moderately_active": 2,
               "very_active": 3, "extremely_active": 4}
    return mapping.get(level, 0)


def build_feature_vector(req: MealRecommendationRequest) -> np.ndarray:
    conditions_lower = [c.lower() for c in req.conditions]
    bmi = req.bmi or (
        req.weight / ((req.height / 100) ** 2)
        if req.weight and req.height else 25.0
    )
    return np.array([[
        req.age or 40,
        bmi,
        encode_activity(req.activityLevel),
        len(req.conditions),
        int(any("diabet" in c for c in conditions_lower)),
        int(any("hypertens" in c for c in conditions_lower)),
        int(any("celiac" in c for c in conditions_lower)),
        int("vegan" in req.dietaryRestrictions),
        int("vegetarian" in req.dietaryRestrictions),
    ]])


def filter_meals_for_restrictions(
    meals: List[MealItem],
    conditions: List[str],
    dietary_restrictions: List[str]
) -> List[MealItem]:
    """Remove meals that conflict with conditions or dietary restrictions."""
    conditions_lower = [c.lower() for c in conditions]
    avoid_keywords = set()

    for condition, rules in CONDITION_OVERRIDES.items():
        if any(condition in c for c in conditions_lower):
            avoid_keywords.update(rules.get("avoid_keywords", []))

    for restriction in dietary_restrictions:
        avoid_keywords.update(DIETARY_RESTRICTION_FILTERS.get(restriction, []))

    filtered = []
    for meal in meals:
        name_lower = meal.name.lower()
        if not any(kw in name_lower for kw in avoid_keywords):
            filtered.append(meal)

    return filtered if filtered else meals  # fallback to unfiltered if all removed


def get_general_advice(conditions: List[str], restrictions: List[str]) -> List[str]:
    advice = ["Stay well hydrated — aim for 6–8 glasses of water daily."]
    conditions_lower = [c.lower() for c in conditions]

    for condition, rules in CONDITION_OVERRIDES.items():
        if any(condition in c for c in conditions_lower):
            advice.append(rules["advice"])

    if "vegan" in restrictions:
        advice.append("Supplement vitamin B12, iron, and omega-3 from plant sources.")
    if "gluten-free" in restrictions:
        advice.append("Ensure gluten-free oats to avoid cross-contamination.")

    return advice


async def get_meal_recommendations(req: MealRecommendationRequest) -> MealRecommendationResponse:
    model = ModelLoader.get_meal_model()

    if model:
        try:
            features = build_feature_vector(req)
            cat_idx = int(model.predict(features)[0])
            category = ["low_cal", "medium_cal", "high_cal"][cat_idx]
        except Exception as e:
            logger.warning(f"Meal model predict failed: {e}, using rule fallback")
            category = _rule_based_category(req)
    else:
        category = _rule_based_category(req)

    logger.info(f"Meal category selected: {category}")
    template = MEAL_DB[category]

    # Filter based on conditions + restrictions
    breakfast = filter_meals_for_restrictions(
        template["breakfast"], req.conditions, req.dietaryRestrictions)
    lunch = filter_meals_for_restrictions(
        template["lunch"], req.conditions, req.dietaryRestrictions)
    dinner = filter_meals_for_restrictions(
        template["dinner"], req.conditions, req.dietaryRestrictions)
    snacks = filter_meals_for_restrictions(
        template["snacks"], req.conditions, req.dietaryRestrictions)

    # Pick one from each (simple selection — could be extended to ranking)
    b = breakfast[:2]
    l = lunch[:2]
    d = dinner[:1]
    s = snacks[:1]

    all_meals = b + l + d + s
    total_cal = sum(m.calories for m in all_meals)
    total_pro = sum(m.protein for m in all_meals)
    total_carb = sum(m.carbs for m in all_meals)
    total_fat = sum(m.fat for m in all_meals)
    total_fiber = sum(m.fiber or 0 for m in all_meals)

    return MealRecommendationResponse(
        breakfast=b,
        lunch=l,
        dinner=d,
        snacks=s,
        nutritionSummary=NutritionSummary(
            totalCalories=total_cal,
            totalProtein=round(total_pro, 1),
            totalCarbs=round(total_carb, 1),
            totalFat=round(total_fat, 1),
            totalFiber=round(total_fiber, 1),
            hydrationGoalLiters=2.5 if (req.activityLevel in ["very_active", "extremely_active"]) else 2.0
        ),
        generalAdvice=get_general_advice(req.conditions, req.dietaryRestrictions)
    )


def _rule_based_category(req: MealRecommendationRequest) -> str:
    """Fallback rule-based category selection."""
    bmi = req.bmi or 25.0
    active = req.activityLevel in ["very_active", "extremely_active"]
    if active and bmi < 25:
        return "high_cal"
    if bmi > 30:
        return "low_cal"
    return "medium_cal"
