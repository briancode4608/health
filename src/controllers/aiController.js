const multer = require('multer');
const path = require('path');
const fs = require('fs');
const aiService = require('../services/aiService');
const User = require('../models/User');

// Multer config for food image uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    const uploadDir = path.join(process.cwd(), 'uploads', 'food');
    fs.mkdirSync(uploadDir, { recursive: true });
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const ext = path.extname(file.originalname).toLowerCase();
    cb(null, `food_${req.user.id}_${Date.now()}${ext}`);
  }
});

const fileFilter = (req, file, cb) => {
  const allowed = ['.jpg', '.jpeg', '.png', '.webp'];
  const ext = path.extname(file.originalname).toLowerCase();
  if (allowed.includes(ext)) {
    cb(null, true);
  } else {
    cb(new Error('Only JPEG, PNG and WebP images are allowed.'));
  }
};

const upload = multer({
  storage,
  fileFilter,
  limits: { fileSize: 5 * 1024 * 1024 } // 5MB
});

/**
 * @route   POST /api/ai/food-scan
 * @access  Private
 */
const scanFood = [
  upload.single('image'),
  async (req, res, next) => {
    try {
      if (!req.file) {
        return res.status(400).json({ error: 'Food image is required.' });
      }

      const result = await aiService.scanFoodImage(req.file.path);

      // Cleanup uploaded file after processing
      fs.unlink(req.file.path, () => {});

      res.json({
        ...result,
        scannedAt: new Date().toISOString()
      });
    } catch (err) {
      // Cleanup on error
      if (req.file?.path) fs.unlink(req.file.path, () => {});
      next(err);
    }
  }
];

/**
 * @route   POST /api/ai/health-insights
 * @access  Private
 */
const getHealthInsights = async (req, res, next) => {
  try {
    const insights = await aiService.generateHealthInsights(req.user.id);
    res.json({ insights, generatedAt: new Date().toISOString() });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/ai/meal-recommendations
 * @access  Private
 */
const getMealRecommendations = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id);
    const payload = {
      age: user.age,
      weight: user.weight,
      height: user.height,
      conditions: user.conditions,
      activityLevel: user.activityLevel,
      dietaryRestrictions: user.dietaryRestrictions,
      ...req.body
    };
    const recommendations = await aiService.getMealRecommendations(payload);
    res.json({ recommendations });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/ai/exercise-recommendations
 * @access  Private
 */
const getExerciseRecommendations = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id);
    const payload = {
      conditions: user.conditions,
      activityLevel: user.activityLevel,
      age: user.age,
      weight: user.weight,
      ...req.body
    };
    const recommendations = await aiService.getExerciseRecommendations(payload);
    res.json({ recommendations });
  } catch (err) {
    next(err);
  }
};

module.exports = { scanFood, getHealthInsights, getMealRecommendations, getExerciseRecommendations };
