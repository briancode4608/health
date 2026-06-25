const mongoose = require('mongoose');

const exerciseLogSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  exerciseType: {
    type: String,
    required: [true, 'Exercise type is required'],
    trim: true,
    enum: [
      'walking', 'running', 'cycling', 'swimming',
      'yoga', 'strength_training', 'stretching',
      'pilates', 'aerobics', 'dancing', 'chair_exercises',
      'water_aerobics', 'tai_chi', 'other'
    ]
  },
  duration: {
    type: Number,
    required: [true, 'Duration is required'],
    min: [1, 'Duration must be at least 1 minute'],
    comment: 'minutes'
  },
  intensity: {
    type: String,
    enum: ['very_light', 'light', 'moderate', 'vigorous', 'very_vigorous'],
    default: 'moderate'
  },
  caloriesBurned: {
    type: Number,
    min: 0
  },
  heartRateAvg: {
    type: Number,
    min: 30,
    max: 250
  },
  notes: { type: String, maxlength: 500 },
  date: {
    type: Date,
    default: Date.now,
    index: true
  },
  completedRecommendation: { type: Boolean, default: false },
  painLevel: {
    type: Number,
    min: 0,
    max: 10,
    comment: '0=none, 10=severe'
  }
}, {
  timestamps: true
});

// Estimate calories burned using MET values
exerciseLogSchema.pre('save', function (next) {
  if (!this.caloriesBurned) {
    const metValues = {
      walking: 3.5, running: 9.0, cycling: 7.5, swimming: 8.0,
      yoga: 2.5, strength_training: 5.0, stretching: 2.3,
      pilates: 3.0, aerobics: 6.5, dancing: 4.8,
      chair_exercises: 2.0, water_aerobics: 4.0,
      tai_chi: 3.0, other: 4.0
    };
    const met = metValues[this.exerciseType] || 4.0;
    // Calories = MET × weight(kg) × hours; assume 70kg if unknown
    this.caloriesBurned = Math.round(met * 70 * (this.duration / 60));
  }
  next();
});

exerciseLogSchema.index({ userId: 1, date: -1 });

module.exports = mongoose.model('ExerciseLog', exerciseLogSchema);
