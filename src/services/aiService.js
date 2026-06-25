const axios = require('axios');
const HealthLog = require('../models/HealthLog');
const MealLog = require('../models/MealLog');
const ExerciseLog = require('../models/ExerciseLog');
const User = require('../models/User');
const fs = require('fs');
const FormData = require('form-data');
const logger = require('../config/logger');

const AI_BASE = process.env.AI_SERVICE_URL || 'http://localhost:8000';

const aiClient = axios.create({
  baseURL: AI_BASE,
  timeout: 30000,
  headers: { 'Content-Type': 'application/json' }
});

// Retry wrapper with exponential backoff
const withRetry = async (fn, retries = 2) => {
  for (let i = 0; i <= retries; i++) {
    try {
      return await fn();
    } catch (err) {
      if (i === retries) throw err;
      await new Promise(r => setTimeout(r, 500 * Math.pow(2, i)));
    }
  }
};

/**
 * Get AI meal recommendations
 */
const getMealRecommendations = async (userProfile) => {
  return withRetry(async () => {
    const { data } = await aiClient.post('/ai/recommend-meals', userProfile);
    return data;
  });
};

/**
 * Get AI exercise recommendations
 */
const getExerciseRecommendations = async (payload) => {
  return withRetry(async () => {
    const { data } = await aiClient.post('/ai/recommend-exercise', payload);
    return data;
  });
};

/**
 * Scan food image for detection + nutrition
 */
const scanFoodImage = async (imagePath) => {
  return withRetry(async () => {
    const form = new FormData();
    form.append('file', fs.createReadStream(imagePath));
    const { data } = await aiClient.post('/ai/food-scan', form, {
      headers: form.getHeaders(),
      timeout: 45000
    });
    return data;
  });
};

/**
 * Generate comprehensive health insights for a user
 * Fetches data, builds context, calls AI microservice
 */
const generateHealthInsights = async (userId) => {
  try {
    const [user, healthLogs, mealLogs, exerciseLogs] = await Promise.all([
      User.findById(userId).select('-password').lean(),
      HealthLog.find({ userId }).sort({ date: -1 }).limit(30).lean(),
      MealLog.find({ userId }).sort({ date: -1 }).limit(30).lean(),
      ExerciseLog.find({ userId }).sort({ date: -1 }).limit(30).lean()
    ]);

    const payload = {
      userProfile: {
        conditions: user.conditions,
        age: user.age,
        activityLevel: user.activityLevel
      },
      healthLogs: healthLogs.map(l => ({
        date: l.date,
        mood: l.mood,
        energyLevel: l.energyLevel,
        sleepHours: l.sleepHours,
        symptoms: l.symptoms,
        painLevel: l.painLevel,
        stressLevel: l.stressLevel
      })),
      mealLogs: mealLogs.map(l => ({
        date: l.date,
        mealType: l.mealType,
        calories: l.calories,
        nutritionSummary: l.nutritionSummary
      })),
      exerciseLogs: exerciseLogs.map(l => ({
        date: l.date,
        exerciseType: l.exerciseType,
        duration: l.duration,
        intensity: l.intensity
      }))
    };

    const { data } = await aiClient.post('/ai/health-insights', payload);
    return data;
  } catch (err) {
    logger.error(`Health insights generation failed: ${err.message}`);
    return { error: 'Insights temporarily unavailable.', insights: [] };
  }
};

module.exports = {
  getMealRecommendations,
  getExerciseRecommendations,
  scanFoodImage,
  generateHealthInsights
};
