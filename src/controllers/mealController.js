const MealLog = require('../models/MealLog');
const User = require('../models/User');
const aiService = require('../services/aiService');
const logger = require('../config/logger');

/**
 * @route   GET /api/meals/recommendations
 * @access  Private
 */
const getRecommendations = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id);

    const payload = {
      age: user.age,
      weight: user.weight,
      height: user.height,
      conditions: user.conditions,
      activityLevel: user.activityLevel,
      dietaryRestrictions: user.dietaryRestrictions,
      bmi: user.bmi
    };

    const recommendations = await aiService.getMealRecommendations(payload);

    res.json({
      recommendations,
      generatedAt: new Date().toISOString(),
      basedOn: {
        conditions: user.conditions,
        activityLevel: user.activityLevel,
        dietaryRestrictions: user.dietaryRestrictions
      }
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/meals/log
 * @access  Private
 */
const logMeal = async (req, res, next) => {
  try {
    const { foodItems, calories, mealType, date, notes, aiRecommendationUsed } = req.body;

    const meal = await MealLog.create({
      userId: req.user.id,
      foodItems,
      calories,
      mealType,
      date: date || new Date(),
      notes,
      aiRecommendationUsed: aiRecommendationUsed || false
    });

    logger.info(`Meal logged: user=${req.user.id}, type=${mealType}`);

    res.status(201).json({ message: 'Meal logged successfully.', meal });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/meals/history
 * @access  Private
 */
const getMealHistory = async (req, res, next) => {
  try {
    const { startDate, endDate, mealType, page = 1, limit = 20 } = req.query;

    const filter = { userId: req.user.id };
    if (startDate || endDate) {
      filter.date = {};
      if (startDate) filter.date.$gte = new Date(startDate);
      if (endDate) filter.date.$lte = new Date(endDate);
    }
    if (mealType) filter.mealType = mealType;

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const [meals, total] = await Promise.all([
      MealLog.find(filter)
        .sort({ date: -1 })
        .skip(skip)
        .limit(parseInt(limit))
        .lean(),
      MealLog.countDocuments(filter)
    ]);

    // Daily summary aggregation
    const dailySummary = await MealLog.aggregate([
      { $match: filter },
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$date' } },
          totalCalories: { $sum: '$calories' },
          mealCount: { $sum: 1 }
        }
      },
      { $sort: { _id: -1 } },
      { $limit: 7 }
    ]);

    res.json({
      meals,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total,
        pages: Math.ceil(total / parseInt(limit))
      },
      dailySummary
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   DELETE /api/meals/:id
 * @access  Private
 */
const deleteMealLog = async (req, res, next) => {
  try {
    const meal = await MealLog.findOneAndDelete({
      _id: req.params.id,
      userId: req.user.id
    });

    if (!meal) {
      return res.status(404).json({ error: 'Meal log not found.' });
    }

    res.json({ message: 'Meal log deleted.' });
  } catch (err) {
    next(err);
  }
};

module.exports = { getRecommendations, logMeal, getMealHistory, deleteMealLog };
