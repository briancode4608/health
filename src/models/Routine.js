const mongoose = require('mongoose');

const routineSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  title: {
    type: String,
    required: [true, 'Routine title is required'],
    trim: true,
    maxlength: [100, 'Title cannot exceed 100 characters']
  },
  time: {
    type: String,
    required: [true, 'Time is required'],
    match: [/^([01]\d|2[0-3]):([0-5]\d)$/, 'Time must be in HH:MM format']
  },
  activityType: {
    type: String,
    required: [true, 'Activity type is required'],
    enum: [
      'medication', 'meal', 'exercise', 'rest',
      'water_intake', 'blood_pressure_check', 'glucose_check',
      'therapy', 'mindfulness', 'custom'
    ]
  },
  description: {
    type: String,
    maxlength: [500, 'Description cannot exceed 500 characters']
  },
  reminderEnabled: {
    type: Boolean,
    default: true
  },
  frequency: {
    type: String,
    enum: ['daily', 'weekdays', 'weekends', 'custom'],
    default: 'daily'
  },
  customDays: [{
    type: String,
    enum: ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
  }],
  isActive: {
    type: Boolean,
    default: true
  },
  color: {
    type: String,
    default: '#4A90E2',
    match: [/^#[0-9A-Fa-f]{6}$/, 'Color must be a valid hex code']
  }
}, {
  timestamps: true
});

routineSchema.index({ userId: 1, time: 1 });

module.exports = mongoose.model('Routine', routineSchema);
