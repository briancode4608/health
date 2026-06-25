const mongoose = require('mongoose');

const symptomSchema = new mongoose.Schema({
  name: { type: String, required: true, trim: true },
  severity: {
    type: Number,
    min: 1,
    max: 10,
    required: true,
    comment: '1=mild, 10=severe'
  },
  duration: { type: String, comment: 'e.g. 2 hours, all day' }
}, { _id: false });

const healthLogSchema = new mongoose.Schema({
  userId: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User',
    required: true,
    index: true
  },
  mood: {
    type: Number,
    min: [1, 'Mood scale 1-10'],
    max: [10, 'Mood scale 1-10'],
    required: [true, 'Mood rating is required'],
    comment: '1=very poor, 10=excellent'
  },
  energyLevel: {
    type: Number,
    min: [1, 'Energy scale 1-10'],
    max: [10, 'Energy scale 1-10'],
    required: [true, 'Energy level is required']
  },
  symptoms: [symptomSchema],
  sleepHours: {
    type: Number,
    min: [0, 'Sleep hours cannot be negative'],
    max: [24, 'Sleep hours cannot exceed 24'],
    required: [true, 'Sleep hours are required']
  },
  sleepQuality: {
    type: Number,
    min: 1,
    max: 10,
    comment: '1=very poor, 10=excellent'
  },
  stressLevel: {
    type: Number,
    min: 1,
    max: 10
  },
  painLevel: {
    type: Number,
    min: 0,
    max: 10
  },
  bloodPressure: {
    systolic: { type: Number, min: 60, max: 250 },
    diastolic: { type: Number, min: 40, max: 150 }
  },
  bloodGlucose: {
    value: { type: Number, min: 0 },
    unit: { type: String, enum: ['mg/dL', 'mmol/L'], default: 'mg/dL' },
    takenWhen: { type: String, enum: ['fasting', 'post_meal', 'random'] }
  },
  medications: [{
    name: String,
    taken: Boolean,
    dosage: String
  }],
  notes: { type: String, maxlength: 1000 },
  date: {
    type: Date,
    default: Date.now,
    index: true
  }
}, {
  timestamps: true,
  toJSON: { virtuals: true }
});

// Virtual: overall wellness score
healthLogSchema.virtual('wellnessScore').get(function () {
  const avgSymptomSeverity = this.symptoms.length > 0
    ? this.symptoms.reduce((s, sym) => s + sym.severity, 0) / this.symptoms.length
    : 0;
  const score = (
    (this.mood * 2) +
    (this.energyLevel * 2) +
    (this.sleepQuality || this.sleepHours >= 7 ? 3 : 1) -
    avgSymptomSeverity
  ) / 7;
  return Math.max(0, Math.min(10, parseFloat(score.toFixed(1))));
});

healthLogSchema.index({ userId: 1, date: -1 });

module.exports = mongoose.model('HealthLog', healthLogSchema);
