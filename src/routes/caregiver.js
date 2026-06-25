const router = require('express').Router();
const {
  getPatients, assignPatient, getPatientLogs, getPatientInsights
} = require('../controllers/caregiverController');
const { protect, authorize, verifyCaregiverAccess } = require('../middleware/auth');
const { validateObjectId } = require('../middleware/validation');
const { body } = require('express-validator');

router.use(protect);

// All caregiver routes require caregiver or admin role
router.get('/patients', authorize('caregiver', 'admin'), getPatients);

router.post('/patients/assign',
  authorize('caregiver'),
  [body('patientEmail').isEmail().withMessage('Valid patient email required')],
  assignPatient
);

router.get('/patient/:id/logs',
  validateObjectId('id'),
  authorize('caregiver', 'admin'),
  verifyCaregiverAccess,
  getPatientLogs
);

router.get('/patient/:id/insights',
  validateObjectId('id'),
  authorize('caregiver', 'admin'),
  verifyCaregiverAccess,
  getPatientInsights
);

module.exports = router;
