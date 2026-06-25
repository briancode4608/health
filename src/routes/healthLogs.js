const router = require('express').Router();
const { createLog, getLogs, getLog, updateLog } = require('../controllers/healthLogController');
const { protect } = require('../middleware/auth');
const { validateHealthLog, validateDateRange, validateObjectId } = require('../middleware/validation');

router.use(protect);

router.post('/', validateHealthLog, createLog);
router.get('/', validateDateRange, getLogs);
router.get('/:id', validateObjectId('id'), getLog);
router.put('/:id', validateObjectId('id'), updateLog);

module.exports = router;
