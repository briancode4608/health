const router = require('express').Router();
const { getRecommendations, logMeal, getMealHistory, deleteMealLog } = require('../controllers/mealController');
const { protect } = require('../middleware/auth');
const { validateMealLog, validateDateRange, validateObjectId } = require('../middleware/validation');

router.use(protect);

router.get('/recommendations', getRecommendations);
router.post('/log', validateMealLog, logMeal);
router.get('/history', validateDateRange, getMealHistory);
router.delete('/:id', validateObjectId('id'), deleteMealLog);

module.exports = router;
