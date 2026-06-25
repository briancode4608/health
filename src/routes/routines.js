const router = require('express').Router();
const { getRoutines, createRoutine, updateRoutine, deleteRoutine } = require('../controllers/routineController');
const { protect } = require('../middleware/auth');
const { validateRoutine, validateObjectId } = require('../middleware/validation');

router.use(protect);

router.get('/', getRoutines);
router.post('/', validateRoutine, createRoutine);
router.put('/:id', validateObjectId('id'), updateRoutine);
router.delete('/:id', validateObjectId('id'), deleteRoutine);

module.exports = router;
