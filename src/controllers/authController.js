const jwt = require('jsonwebtoken');
const User = require('../models/User');
const logger = require('../config/logger');

/**
 * Generate JWT token
 */
const generateToken = (id, role) => {
  return jwt.sign({ id, role }, process.env.JWT_SECRET, {
    expiresIn: process.env.JWT_EXPIRES_IN || '7d'
  });
};

/**
 * @route   POST /api/auth/register
 * @access  Public
 */
const register = async (req, res, next) => {
  try {
    const { name, email, password, role, age, weight, height,
      conditions, dietaryRestrictions, activityLevel } = req.body;

    // Check existing user
    const existingUser = await User.findOne({ email });
    if (existingUser) {
      return res.status(400).json({ error: 'Email already registered.' });
    }

    const user = await User.create({
      name, email, password,
      role: role || 'user',
      age, weight, height,
      conditions: conditions || [],
      dietaryRestrictions: dietaryRestrictions || [],
      activityLevel: activityLevel || 'sedentary'
    });

    const token = generateToken(user._id, user.role);

    logger.info(`New user registered: ${user.email} [${user.role}]`);

    res.status(201).json({
      message: 'Account created successfully.',
      token,
      user: user.toSafeObject()
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/auth/login
 * @access  Public
 */
const login = async (req, res, next) => {
  try {
    const { email, password } = req.body;

    const user = await User.findOne({ email }).select('+password');
    if (!user) {
      return res.status(401).json({ error: 'Invalid credentials.' });
    }

    if (!user.isActive) {
      return res.status(403).json({ error: 'Account is deactivated. Contact support.' });
    }

    const isMatch = await user.comparePassword(password);
    if (!isMatch) {
      return res.status(401).json({ error: 'Invalid credentials.' });
    }

    // Update last login
    user.lastLogin = new Date();
    await user.save({ validateBeforeSave: false });

    const token = generateToken(user._id, user.role);

    logger.info(`User logged in: ${user.email}`);

    res.json({
      message: 'Login successful.',
      token,
      user: user.toSafeObject()
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/auth/me
 * @access  Private
 */
const getMe = async (req, res, next) => {
  try {
    const user = await User.findById(req.user.id).populate('patients', 'name email');
    res.json({ user: user.toSafeObject() });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   PUT /api/auth/profile
 * @access  Private
 */
const updateProfile = async (req, res, next) => {
  try {
    const allowedFields = ['name', 'age', 'weight', 'height',
      'conditions', 'dietaryRestrictions', 'activityLevel'];

    const updates = {};
    allowedFields.forEach(field => {
      if (req.body[field] !== undefined) updates[field] = req.body[field];
    });

    const user = await User.findByIdAndUpdate(
      req.user.id,
      updates,
      { new: true, runValidators: true }
    );

    res.json({ message: 'Profile updated.', user: user.toSafeObject() });
  } catch (err) {
    next(err);
  }
};

module.exports = { register, login, getMe, updateProfile };
