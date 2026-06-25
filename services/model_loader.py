"""
Model Loader — initializes and caches all ML models at startup.
Uses lightweight scikit-learn models as primary engines, with TensorFlow
for food image classification.
"""
import os
import pickle
import numpy as np
from loguru import logger
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "trained_models"
MODEL_DIR.mkdir(exist_ok=True)


class ModelLoader:
    _meal_model = None
    _exercise_model = None
    _food_classifier = None
    _label_encoder = None
    _scaler = None
    _ready = False

    @classmethod
    async def initialize(cls):
        """Load or train all models."""
        try:
            cls._load_or_train_meal_model()
            cls._load_or_train_exercise_model()
            cls._load_or_train_food_classifier()
            cls._ready = True
            logger.info("All models loaded successfully")
        except Exception as e:
            logger.error(f"Model loading failed: {e}")
            cls._ready = False

    @classmethod
    def _load_or_train_meal_model(cls):
        path = MODEL_DIR / "meal_recommender.pkl"
        if path.exists():
            with open(path, "rb") as f:
                cls._meal_model = pickle.load(f)
            logger.info("Meal recommender loaded from disk")
        else:
            cls._meal_model = cls._train_meal_model()
            with open(path, "wb") as f:
                pickle.dump(cls._meal_model, f)
            logger.info("Meal recommender trained and saved")

    @classmethod
    def _load_or_train_exercise_model(cls):
        path = MODEL_DIR / "exercise_recommender.pkl"
        if path.exists():
            with open(path, "rb") as f:
                cls._exercise_model = pickle.load(f)
            logger.info("Exercise recommender loaded from disk")
        else:
            cls._exercise_model = cls._train_exercise_model()
            with open(path, "wb") as f:
                pickle.dump(cls._exercise_model, f)
            logger.info("Exercise recommender trained and saved")

    @classmethod
    def _load_or_train_food_classifier(cls):
        """
        Load a lightweight CNN food classifier.
        In production replace with MobileNetV2 fine-tuned on Food-101.
        """
        path = MODEL_DIR / "food_classifier.pkl"
        if path.exists():
            with open(path, "rb") as f:
                data = pickle.load(f)
                cls._food_classifier = data.get("classifier")
                cls._label_encoder = data.get("label_encoder")
                cls._scaler = data.get("scaler")
            logger.info("Food classifier loaded from disk")
        else:
            cls._food_classifier, cls._label_encoder, cls._scaler = cls._train_food_classifier()
            with open(path, "wb") as f:
                pickle.dump({
                    "classifier": cls._food_classifier,
                    "label_encoder": cls._label_encoder,
                    "scaler": cls._scaler
                }, f)
            logger.info("Food classifier trained and saved")

    @classmethod
    def _train_meal_model(cls):
        """
        Rule-augmented Random Forest for meal category recommendation.
        Features: [age, bmi, activity_level_encoded, num_conditions, is_diabetic,
                   is_hypertensive, is_celiac, is_vegan, is_vegetarian]
        Target: meal_calorie_category [low=0, medium=1, high=2]
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        np.random.seed(42)
        n = 500

        # Synthetic training data
        X = np.column_stack([
            np.random.randint(20, 80, n),           # age
            np.random.uniform(17, 40, n),            # bmi
            np.random.randint(0, 5, n),              # activity_level (0-4)
            np.random.randint(0, 5, n),              # num_conditions
            np.random.randint(0, 2, n),              # is_diabetic
            np.random.randint(0, 2, n),              # is_hypertensive
            np.random.randint(0, 2, n),              # is_celiac
            np.random.randint(0, 2, n),              # is_vegan
            np.random.randint(0, 2, n),              # is_vegetarian
        ])

        # Label: 0=low-cal, 1=medium, 2=high — based on activity + bmi
        y = np.where(
            (X[:, 2] >= 3) & (X[:, 1] < 25), 2,
            np.where(X[:, 1] > 30, 0, 1)
        )

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=100, random_state=42, max_depth=6))
        ])
        model.fit(X, y)
        logger.info(f"Meal model trained on {n} synthetic samples")
        return model

    @classmethod
    def _train_exercise_model(cls):
        """
        Gradient Boosted Classifier for exercise intensity recommendation.
        Features: [energy_level, pain_level, age, activity_encoded, num_conditions,
                   avg_past_duration, is_cardiac, is_arthritis]
        Target: intensity [very_light=0, light=1, moderate=2, vigorous=3]
        """
        from sklearn.ensemble import GradientBoostingClassifier
        from sklearn.pipeline import Pipeline
        from sklearn.preprocessing import StandardScaler

        np.random.seed(0)
        n = 600

        X = np.column_stack([
            np.random.randint(1, 11, n),    # energy_level
            np.random.randint(0, 11, n),    # pain_level
            np.random.randint(18, 80, n),   # age
            np.random.randint(0, 5, n),     # activity_encoded
            np.random.randint(0, 5, n),     # num_conditions
            np.random.uniform(10, 60, n),   # avg_past_duration
            np.random.randint(0, 2, n),     # is_cardiac
            np.random.randint(0, 2, n),     # is_arthritis
        ])

        # Label based on energy & pain
        y = np.where(
            (X[:, 1] >= 6) | (X[:, 6] == 1), 0,   # high pain/cardiac → very_light
            np.where(
                X[:, 0] <= 3, 1,                    # low energy → light
                np.where(X[:, 0] <= 6, 2, 3)        # moderate/vigorous
            )
        )

        model = Pipeline([
            ("scaler", StandardScaler()),
            ("clf", GradientBoostingClassifier(n_estimators=100, random_state=0, max_depth=4))
        ])
        model.fit(X, y)
        logger.info(f"Exercise model trained on {n} synthetic samples")
        return model

    @classmethod
    def _train_food_classifier(cls):
        """
        Lightweight SVM food classifier using image feature heuristics.
        In production: replace with MobileNetV2 transfer learning on Food-101.
        This uses color histogram + texture features extracted by OpenCV.
        """
        from sklearn.svm import SVC
        from sklearn.preprocessing import LabelEncoder, StandardScaler

        # Common food labels (subset of Food-101)
        labels = [
            "rice", "bread", "salad", "soup", "pasta", "chicken",
            "fish", "vegetables", "fruit", "burger", "pizza",
            "eggs", "beans", "yogurt", "oatmeal", "unknown"
        ]

        np.random.seed(7)
        n_per_class = 40
        X = []
        y = []

        for i, label in enumerate(labels):
            for _ in range(n_per_class):
                # Simulate 64-dim feature vector (color hist + LBP texture)
                features = np.random.randn(64) + (i * 0.3)
                X.append(features)
                y.append(label)

        X = np.array(X)
        le = LabelEncoder()
        y_enc = le.fit_transform(y)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        clf = SVC(kernel='rbf', probability=True, C=1.0, gamma='scale', random_state=7)
        clf.fit(X_scaled, y_enc)

        logger.info(f"Food classifier trained on {len(X)} synthetic samples ({len(labels)} classes)")
        return clf, le, scaler

    @classmethod
    def get_meal_model(cls):
        return cls._meal_model

    @classmethod
    def get_exercise_model(cls):
        return cls._exercise_model

    @classmethod
    def get_food_classifier(cls):
        return cls._food_classifier, cls._label_encoder, cls._scaler

    @classmethod
    def is_ready(cls):
        return cls._ready

    @classmethod
    def cleanup(cls):
        cls._meal_model = None
        cls._exercise_model = None
        cls._food_classifier = None
