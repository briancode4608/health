const router = require('express').Router();
const { scanFood, getHealthInsights, getMealRecommendations, getExerciseRecommendations } = require('../controllers/aiController');
const { protect } = require('../middleware/auth');

router.use(protect);

router.post('/food-scan', scanFood);
router.post('/health-insights', getHealthInsights);
router.post('/meal-recommendations', getMealRecommendations);
router.post('/exercise-recommendations', getExerciseRecommendations);

module.exports = router;
