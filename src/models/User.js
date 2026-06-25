const mongoose = require('mongoose');
const bcrypt = require('bcryptjs');

const userSchema = new mongoose.Schema({
  name: {
    type: String,
    required: [true, 'Name is required'],
    trim: true,
    minlength: [2, 'Name must be at least 2 characters'],
    maxlength: [100, 'Name cannot exceed 100 characters']
  },
  email: {
    type: String,
    required: [true, 'Email is required'],
    unique: true,
    lowercase: true,
    trim: true,
    match: [/^\S+@\S+\.\S+$/, 'Please provide a valid email']
  },
  password: {
    type: String,
    required: [true, 'Password is required'],
    minlength: [8, 'Password must be at least 8 characters'],
    select: false
  },
  role: {
    type: String,
    enum: ['user', 'caregiver', 'admin'],
    default: 'user'
  },
  age: {
    type: Number,
    min: [1, 'Age must be positive'],
    max: [150, 'Age value is unrealistic']
  },
  weight: {
    type: Number,
    min: [1, 'Weight must be positive'],
    comment: 'in kg'
  },
  height: {
    type: Number,
    min: [1, 'Height must be positive'],
    comment: 'in cm'
  },
  conditions: [{
    type: String,
    trim: true
  }],
  dietaryRestrictions: [{
    type: String,
    trim: true,
    enum: [
      'vegetarian', 'vegan', 'gluten-free', 'dairy-free',
      'nut-free', 'halal', 'kosher', 'low-sodium',
      'low-sugar', 'diabetic-friendly', 'none', 'other'
    ]
  }],
  activityLevel: {
    type: String,
    enum: ['sedentary', 'lightly_active', 'moderately_active', 'very_active', 'extremely_active'],
    default: 'sedentary'
  },
  // Caregiver-patient relationship
  patients: [{
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  }],
  caregiver: {
    type: mongoose.Schema.Types.ObjectId,
    ref: 'User'
  },
  isActive: {
    type: Boolean,
    default: true
  },
  lastLogin: Date,
  profileComplete: {
    type: Boolean,
    default: false
  }
}, {
  timestamps: true,
  toJSON: { virtuals: true },
  toObject: { virtuals: true }
});

// Virtual: BMI calculation
userSchema.virtual('bmi').get(function () {
  if (this.weight && this.height) {
    const heightM = this.height / 100;
    return parseFloat((this.weight / (heightM * heightM)).toFixed(1));
  }
  return null;
});

// Hash password before save
userSchema.pre('save', async function (next) {
  if (!this.isModified('password')) return next();
  const rounds = parseInt(process.env.BCRYPT_ROUNDS) || 12;
  this.password = await bcrypt.hash(this.password, rounds);

  // Mark profile complete if core fields are filled
  this.profileComplete = !!(this.age && this.weight && this.height && this.conditions.length);
  next();
});

// Instance method: compare passwords
userSchema.methods.comparePassword = async function (candidatePassword) {
  return bcrypt.compare(candidatePassword, this.password);
};

// Instance method: safe user object (no password)
userSchema.methods.toSafeObject = function () {
  const obj = this.toObject();
  delete obj.password;
  return obj;
};

// Index for performance
userSchema.index({ email: 1 });
userSchema.index({ role: 1 });

module.exports = mongoose.model('User', userSchema);
