"""
Food Detection Service
Uses OpenCV for image preprocessing + feature extraction,
then SVM classifier for food category identification.
In production: replace SVM with fine-tuned MobileNetV2 on Food-101.
"""
import cv2
import numpy as np
from pathlib import Path
from loguru import logger
from typing import Tuple, Dict, Any

from services.model_loader import ModelLoader
from models.schemas import FoodScanResponse, FoodNutrition

# ── Nutrition Database ───────────────────────────────────────────────────────
# Per 100g reference values
NUTRITION_DB: Dict[str, Dict] = {
    "rice":        {"calories": 130, "protein": 2.7, "carbs": 28, "fat": 0.3, "fiber": 0.4, "sodium": 1},
    "bread":       {"calories": 265, "protein": 9,   "carbs": 49, "fat": 3.2, "fiber": 2.7, "sodium": 491},
    "salad":       {"calories": 20,  "protein": 1.5, "carbs": 3.5,"fat": 0.3, "fiber": 2.0, "sodium": 15},
    "soup":        {"calories": 60,  "protein": 3.5, "carbs": 8,  "fat": 1.5, "fiber": 1.5, "sodium": 450},
    "pasta":       {"calories": 131, "protein": 5,   "carbs": 25, "fat": 1.1, "fiber": 1.8, "sodium": 6},
    "chicken":     {"calories": 165, "protein": 31,  "carbs": 0,  "fat": 3.6, "fiber": 0,   "sodium": 74},
    "fish":        {"calories": 136, "protein": 20,  "carbs": 0,  "fat": 5,   "fiber": 0,   "sodium": 64},
    "vegetables":  {"calories": 35,  "protein": 2,   "carbs": 7,  "fat": 0.2, "fiber": 3.0, "sodium": 40},
    "fruit":       {"calories": 60,  "protein": 0.8, "carbs": 15, "fat": 0.2, "fiber": 2.5, "sodium": 2},
    "burger":      {"calories": 295, "protein": 17,  "carbs": 24, "fat": 14,  "fiber": 1.5, "sodium": 396},
    "pizza":       {"calories": 266, "protein": 11,  "carbs": 33, "fat": 10,  "fiber": 2.3, "sodium": 598},
    "eggs":        {"calories": 155, "protein": 13,  "carbs": 1.1,"fat": 11,  "fiber": 0,   "sodium": 124},
    "beans":       {"calories": 127, "protein": 8.7, "carbs": 22, "fat": 0.5, "fiber": 6.4, "sodium": 240},
    "yogurt":      {"calories": 100, "protein": 10,  "carbs": 7,  "fat": 3.8, "fiber": 0,   "sodium": 50},
    "oatmeal":     {"calories": 71,  "protein": 2.5, "carbs": 12, "fat": 1.5, "fiber": 1.7, "sodium": 49},
    "unknown":     {"calories": 200, "protein": 10,  "carbs": 25, "fat": 8,   "fiber": 2,   "sodium": 200},
}

ALLERGEN_DB: Dict[str, list] = {
    "bread": ["gluten", "wheat"],
    "pasta": ["gluten", "wheat"],
    "pizza": ["gluten", "wheat", "dairy"],
    "burger": ["gluten", "wheat"],
    "yogurt": ["dairy"],
    "eggs": ["eggs"],
    "fish": ["fish"],
    "chicken": [],
    "rice": [],
    "salad": [],
    "soup": [],
    "vegetables": [],
    "fruit": [],
    "beans": [],
    "oatmeal": ["gluten"],
    "unknown": [],
}

HEALTH_SCORE_DB: Dict[str, int] = {
    "salad": 9, "vegetables": 9, "fruit": 8, "oatmeal": 8,
    "beans": 8, "fish": 8, "chicken": 7, "eggs": 7,
    "yogurt": 7, "soup": 6, "rice": 6, "pasta": 5,
    "bread": 5, "burger": 3, "pizza": 3, "unknown": 5
}

PORTION_ESTIMATES = {
    "salad": "1 bowl (~200g)", "soup": "1 bowl (~300ml)",
    "rice": "1 cup cooked (~200g)", "pasta": "1 portion (~180g)",
    "bread": "2 slices (~60g)", "chicken": "1 breast (~150g)",
    "fish": "1 fillet (~150g)", "burger": "1 burger (~200g)",
    "pizza": "2 slices (~200g)", "eggs": "2 eggs (~100g)",
    "beans": "1 cup cooked (~170g)", "yogurt": "1 cup (~200g)",
    "oatmeal": "1 bowl (~250g)", "vegetables": "1 cup (~100g)",
    "fruit": "1 portion (~150g)", "unknown": "1 serving (~150g)"
}


def preprocess_image(image_path: str) -> np.ndarray:
    """Load and preprocess image for feature extraction."""
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # Resize to standard size
    img = cv2.resize(img, (224, 224))

    # Denoise
    img = cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)

    return img


def extract_color_histogram(img: np.ndarray) -> np.ndarray:
    """Extract HSV color histogram features (32 bins per channel = 96 features)."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    hist_h = cv2.calcHist([hsv], [0], None, [32], [0, 180]).flatten()
    hist_s = cv2.calcHist([hsv], [1], None, [16], [0, 256]).flatten()
    hist_v = cv2.calcHist([hsv], [2], None, [16], [0, 256]).flatten()
    features = np.concatenate([hist_h, hist_s, hist_v])
    # Normalise
    norm = np.linalg.norm(features)
    return features / (norm + 1e-8)


def extract_texture_features(img: np.ndarray) -> np.ndarray:
    """
    Extract texture using Local Binary Pattern (LBP) approximation.
    Uses Sobel gradient magnitude histogram as lightweight alternative.
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    sobelx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    sobely = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    magnitude = np.sqrt(sobelx**2 + sobely**2)

    # Divide into 2x2 grid and compute stats per cell
    h, w = magnitude.shape
    features = []
    for i in range(2):
        for j in range(2):
            cell = magnitude[i*h//2:(i+1)*h//2, j*w//2:(j+1)*w//2]
            features.extend([cell.mean(), cell.std()])

    return np.array(features)  # 8 features


def extract_features(img: np.ndarray) -> np.ndarray:
    """Combine color histogram (64 features) + texture (8 features) = 64 total."""
    color = extract_color_histogram(img)[:56]  # truncate to 56
    texture = extract_texture_features(img)     # 8
    return np.concatenate([color, texture])     # 64 total


async def classify_food(image_path: str) -> FoodScanResponse:
    """
    Main food classification pipeline:
    1. Preprocess image with OpenCV
    2. Extract color + texture features
    3. Run SVM classifier
    4. Return food label + nutrition data
    """
    clf, le, scaler = ModelLoader.get_food_classifier()

    img = preprocess_image(image_path)
    features = extract_features(img).reshape(1, -1)

    if clf and scaler and le:
        try:
            features_scaled = scaler.transform(features)
            probabilities = clf.predict_proba(features_scaled)[0]
            class_indices = np.argsort(probabilities)[::-1]

            top_label = le.inverse_transform([class_indices[0]])[0]
            top_confidence = float(probabilities[class_indices[0]])

            alternatives = []
            for idx in class_indices[1:4]:
                alt_label = le.inverse_transform([idx])[0]
                alternatives.append({
                    "food": alt_label,
                    "confidence": round(float(probabilities[idx]), 3)
                })

            logger.info(f"Food detected: {top_label} (confidence={top_confidence:.2f})")
        except Exception as e:
            logger.warning(f"Classifier failed: {e}, using fallback")
            top_label = "unknown"
            top_confidence = 0.5
            alternatives = []
    else:
        # Heuristic fallback: detect dominant color to guess food
        top_label, top_confidence = _color_heuristic(img)
        alternatives = []

    # Get nutrition data (scale for estimated portion)
    nutrition_ref = NUTRITION_DB.get(top_label, NUTRITION_DB["unknown"])
    portion_g = _estimate_portion_grams(top_label)
    scale = portion_g / 100

    nutrition = FoodNutrition(
        calories=int(nutrition_ref["calories"] * scale),
        protein=round(nutrition_ref["protein"] * scale, 1),
        carbs=round(nutrition_ref["carbs"] * scale, 1),
        fat=round(nutrition_ref["fat"] * scale, 1),
        fiber=round(nutrition_ref.get("fiber", 0) * scale, 1),
        sodium=round(nutrition_ref.get("sodium", 0) * scale, 1)
    )

    return FoodScanResponse(
        detectedFood=top_label.replace("_", " ").title(),
        confidence=round(top_confidence, 3),
        alternativeDetections=alternatives,
        estimatedCalories=nutrition.calories,
        nutritionData=nutrition,
        portionEstimate=PORTION_ESTIMATES.get(top_label, "1 serving (~150g)"),
        healthScore=HEALTH_SCORE_DB.get(top_label, 5),
        allergenWarnings=ALLERGEN_DB.get(top_label, [])
    )


def _estimate_portion_grams(food_label: str) -> float:
    """Return reference portion weight in grams."""
    portions = {
        "salad": 200, "soup": 300, "rice": 200, "pasta": 180,
        "bread": 60, "chicken": 150, "fish": 150, "burger": 200,
        "pizza": 200, "eggs": 100, "beans": 170, "yogurt": 200,
        "oatmeal": 250, "vegetables": 100, "fruit": 150, "unknown": 150
    }
    return portions.get(food_label, 150)


def _color_heuristic(img: np.ndarray) -> Tuple[str, float]:
    """Guess food from dominant colour when classifier unavailable."""
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    mean_hue = float(np.mean(hsv[:, :, 0]))
    mean_sat = float(np.mean(hsv[:, :, 1]))

    if mean_sat < 30:
        return "rice", 0.4        # low saturation → white/grey food
    if 15 < mean_hue < 40:
        return "bread", 0.4       # orange-brown tones
    if 35 < mean_hue < 85:
        return "salad", 0.4       # green
    if mean_hue < 15 or mean_hue > 160:
        return "burger", 0.3      # red
    return "unknown", 0.3
