const mongoose = require('mongoose');

const foodItemSchema = new mongoose.Schema({
  name: { type: String, required: true, trim: true },
  portion: { type: String, default: '1 serving' },
  calories: { type: Number, min: 0 },
  protein: { type: Number, min: 0, comment: 'grams' },
  carbs: { type: Number, min: 0, comment: 'grams' },
  fat: { type: Number, min: 0, comment: 'grams' },
  fiber: { type: Number, min: 0, comment: 'grams' },
  sodium: { type: Number, min: 0, comment: 'mg' },
  detectedByAI: { type: Boolean, default: false },
  confidence: { type: Number, min: 0, max: 1 }
}, { _id: false });

const mealLogSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  foodItems: {
    type: [foodItemSchema],
    validate: {
      validator: (v) => v.length > 0,
      message: 'At least one food item is required'
    }
  },
  calories: {
    type: Number,
    min: [0, 'Calories cannot be negative']
  },
  mealType: {
    type: String,
    enum: ['breakfast', 'lunch', 'dinner', 'snack', 'other'],
    required: [true, 'Meal type is required']
  },
  date: {
    type: Date,
    default: Date.now,
    index: true
  },
  notes: { type: String, maxlength: 500 },
  imageUrl: String,
  aiRecommendationUsed: { type: Boolean, default: false },
  nutritionSummary: {
    totalProtein: Number,
    totalCarbs: Number,
    totalFat: Number,
    totalFiber: Number
  }
}, {
  timestamps: true,
  toJSON: { virtuals: true }
});

// Auto-calculate total calories from food items if not provided
mealLogSchema.pre('save', function (next) {
  if (!this.calories && this.foodItems.length > 0) {
    this.calories = this.foodItems.reduce((sum, item) => sum + (item.calories || 0), 0);
  }
  // Auto-calculate nutrition summary
  this.nutritionSummary = {
    totalProtein: this.foodItems.reduce((s, i) => s + (i.protein || 0), 0),
    totalCarbs: this.foodItems.reduce((s, i) => s + (i.carbs || 0), 0),
    totalFat: this.foodItems.reduce((s, i) => s + (i.fat || 0), 0),
    totalFiber: this.foodItems.reduce((s, i) => s + (i.fiber || 0), 0)
  };
  next();
});

// Compound index for efficient user history queries
mealLogSchema.index({ userId: 1, date: -1 });

module.exports = mongoose.model('MealLog', mealLogSchema);
