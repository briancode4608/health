const router = require('express').Router();
const { getRecommendations, logExercise, getExerciseHistory } = require('../controllers/exerciseController');
const { protect } = require('../middleware/auth');
const { validateExerciseLog, validateDateRange } = require('../middleware/validation');

router.use(protect);

router.get('/recommendations', getRecommendations);
router.post('/log', validateExerciseLog, logExercise);
router.get('/history', validateDateRange, getExerciseHistory);

module.exports = router;
