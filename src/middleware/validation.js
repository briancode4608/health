const { body, param, query, validationResult } = require('express-validator');

/**
 * Centralized validation error handler
 */
const handleValidation = (req, res, next) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({
      error: 'Validation failed',
      details: errors.array().map(e => ({ field: e.path, message: e.msg }))
    });
  }
  next();
};

// Auth validation
const validateRegister = [
  body('name').trim().isLength({ min: 2, max: 100 }).withMessage('Name must be 2-100 characters'),
  body('email').isEmail().normalizeEmail().withMessage('Valid email required'),
  body('password')
    .isLength({ min: 8 }).withMessage('Password must be at least 8 characters')
    .matches(/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/)
    .withMessage('Password must contain uppercase, lowercase, and number'),
  body('role').optional().isIn(['user', 'caregiver']).withMessage('Invalid role'),
  handleValidation
];

const validateLogin = [
  body('email').isEmail().normalizeEmail().withMessage('Valid email required'),
  body('password').notEmpty().withMessage('Password is required'),
  handleValidation
];

// Meal validation
const validateMealLog = [
  body('foodItems').isArray({ min: 1 }).withMessage('At least one food item required'),
  body('foodItems.*.name').trim().notEmpty().withMessage('Food item name required'),
  body('foodItems.*.calories').optional().isFloat({ min: 0 }).withMessage('Calories must be positive'),
  body('mealType').isIn(['breakfast', 'lunch', 'dinner', 'snack', 'other'])
    .withMessage('Invalid meal type'),
  body('date').optional().isISO8601().withMessage('Invalid date format'),
  handleValidation
];

// Exercise validation
const validateExerciseLog = [
  body('exerciseType').trim().notEmpty().withMessage('Exercise type is required'),
  body('duration').isInt({ min: 1, max: 600 }).withMessage('Duration must be 1-600 minutes'),
  body('intensity').optional()
    .isIn(['very_light', 'light', 'moderate', 'vigorous', 'very_vigorous'])
    .withMessage('Invalid intensity level'),
  body('date').optional().isISO8601().withMessage('Invalid date format'),
  handleValidation
];

// Health log validation
const validateHealthLog = [
  body('mood').isInt({ min: 1, max: 10 }).withMessage('Mood must be 1-10'),
  body('energyLevel').isInt({ min: 1, max: 10 }).withMessage('Energy level must be 1-10'),
  body('sleepHours').isFloat({ min: 0, max: 24 }).withMessage('Sleep hours must be 0-24'),
  body('symptoms').optional().isArray().withMessage('Symptoms must be an array'),
  body('symptoms.*.name').optional().trim().notEmpty().withMessage('Symptom name required'),
  body('symptoms.*.severity').optional().isInt({ min: 1, max: 10 })
    .withMessage('Symptom severity must be 1-10'),
  body('date').optional().isISO8601().withMessage('Invalid date format'),
  handleValidation
];

// Routine validation
const validateRoutine = [
  body('title').trim().isLength({ min: 1, max: 100 }).withMessage('Title is required (max 100 chars)'),
  body('time').matches(/^([01]\d|2[0-3]):([0-5]\d)$/).withMessage('Time must be HH:MM format'),
  body('activityType')
    .isIn(['medication', 'meal', 'exercise', 'rest', 'water_intake',
      'blood_pressure_check', 'glucose_check', 'therapy', 'mindfulness', 'custom'])
    .withMessage('Invalid activity type'),
  body('frequency').optional()
    .isIn(['daily', 'weekdays', 'weekends', 'custom'])
    .withMessage('Invalid frequency'),
  handleValidation
];

// Parameter validation
const validateObjectId = (paramName = 'id') => [
  param(paramName).isMongoId().withMessage(`Invalid ${paramName} format`),
  handleValidation
];

// Query validation for history endpoints
const validateDateRange = [
  query('startDate').optional().isISO8601().withMessage('Invalid start date'),
  query('endDate').optional().isISO8601().withMessage('Invalid end date'),
  query('limit').optional().isInt({ min: 1, max: 100 }).withMessage('Limit must be 1-100'),
  query('page').optional().isInt({ min: 1 }).withMessage('Page must be positive'),
  handleValidation
];

module.exports = {
  validateRegister,
  validateLogin,
  validateMealLog,
  validateExerciseLog,
  validateHealthLog,
  validateRoutine,
  validateObjectId,
  validateDateRange
};
