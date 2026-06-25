const ExerciseLog = require('../models/ExerciseLog');
const HealthLog = require('../models/HealthLog');
const User = require('../models/User');
const aiService = require('../services/aiService');

/**
 * @route   GET /api/exercise/recommendations
 * @access  Private
 */
const getRecommendations = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id);

    // Get recent energy levels and exercise history
    const recentHealthLog = await HealthLog.findOne({ userId: req.user.id })
      .sort({ date: -1 });

    const recentExercises = await ExerciseLog.find({ userId: req.user.id })
      .sort({ date: -1 })
      .limit(7)
      .select('exerciseType duration intensity date caloriesBurned')
      .lean();

    const payload = {
      condition: user.conditions,
      activityLevel: user.activityLevel,
      age: user.age,
      weight: user.weight,
      energyLevel: recentHealthLog?.energyLevel || 5,
      painLevel: recentHealthLog?.painLevel || 0,
      exerciseHistory: recentExercises
    };

    const recommendations = await aiService.getExerciseRecommendations(payload);

    res.json({
      recommendations,
      generatedAt: new Date().toISOString(),
      currentEnergyLevel: recentHealthLog?.energyLevel
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/exercise/log
 * @access  Private
 */
const logExercise = async (req, res, next) => {
  try {
    const { exerciseType, duration, intensity, heartRateAvg, notes, date, painLevel } = req.body;

    const log = await ExerciseLog.create({
      userId: req.user.id,
      exerciseType,
      duration,
      intensity: intensity || 'moderate',
      heartRateAvg,
      notes,
      date: date || new Date(),
      painLevel
    });

    res.status(201).json({ message: 'Exercise logged successfully.', log });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/exercise/history
 * @access  Private
 */
const getExerciseHistory = async (req, res, next) => {
  try {
    const { startDate, endDate, exerciseType, page = 1, limit = 20 } = req.query;

    const filter = { userId: req.user.id };
    if (startDate || endDate) {
      filter.date = {};
      if (startDate) filter.date.$gte = new Date(startDate);
      if (endDate) filter.date.$lte = new Date(endDate);
    }
    if (exerciseType) filter.exerciseType = exerciseType;

    const skip = (parseInt(page) - 1) * parseInt(limit);

    const [logs, total] = await Promise.all([
      ExerciseLog.find(filter)
        .sort({ date: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      ExerciseLog.countDocuments(filter)
    ]);

    // Weekly stats
    const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    const weeklyStats = await ExerciseLog.aggregate([
      { $match: { userId: req.user.id, date: { $gte: weekAgo } } },
      {
        $group: {
          _id: null,
          totalMinutes: { $sum: '$duration' },
          totalCalories: { $sum: '$caloriesBurned' },
          sessionCount: { $sum: 1 },
          avgIntensity: { $avg: { $switch: {
            branches: [
              { case: { $eq: ['$intensity', 'very_light'] }, then: 1 },
              { case: { $eq: ['$intensity', 'light'] }, then: 2 },
              { case: { $eq: ['$intensity', 'moderate'] }, then: 3 },
              { case: { $eq: ['$intensity', 'vigorous'] }, then: 4 },
              { case: { $eq: ['$intensity', 'very_vigorous'] }, then: 5 }
            ],
            default: 3
          }}}
        }
      }
    ]);

    res.json({
      logs,
      pagination: {
        page: parseInt(page), limit: parseInt(limit), total,
        pages: Math.ceil(total / parseInt(limit))
      },
      weeklyStats: weeklyStats[0] || { totalMinutes: 0, totalCalories: 0, sessionCount: 0 }
    });
  } catch (err) {
    next(err);
  }
};

module.exports = { getRecommendations, logExercise, getExerciseHistory };
