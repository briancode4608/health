const jwt = require('jsonwebtoken');
const User = require('../models/User');
const logger = require('../config/logger');

/**
 * Protect routes - verifies JWT and attaches user to request
 */
const protect = async (req, res, next) => {
  try {
    let token;

    if (req.headers.authorization?.startsWith('Bearer ')) {
      token = req.headers.authorization.split(' ')[1];
    } else if (req.cookies?.token) {
      token = req.cookies.token;
    }

    if (!token) {
      return res.status(401).json({ error: 'Access denied. No token provided.' });
    }

    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    const user = await User.findById(decoded.id).select('-password');

    if (!user || !user.isActive) {
      return res.status(401).json({ error: 'Token is invalid or user is deactivated.' });
    }

    req.user = user;
    next();
  } catch (err) {
    logger.warn(`Auth failed: ${err.message}`);
    if (err.name === 'TokenExpiredError') {
      return res.status(401).json({ error: 'Token has expired.' });
    }
    return res.status(401).json({ error: 'Invalid token.' });
  }
};

/**
 * Authorize specific roles
 * @param {...string} roles - Allowed roles
 */
const authorize = (...roles) => {
  return (req, res, next) => {
    if (!roles.includes(req.user.role)) {
      return res.status(403).json({
        error: `Access denied. Role '${req.user.role}' is not authorized for this action.`
      });
    }
    next();
  };
};

/**
 * Caregiver access: verify caregiver has access to requested patient
 */
const verifyCaregiverAccess = async (req, res, next) => {
  try {
    const patientId = req.params.id;
    const caregiver = req.user;

    if (caregiver.role === 'admin') return next();

    if (caregiver.role !== 'caregiver') {
      return res.status(403).json({ error: 'Only caregivers can access patient data.' });
    }

    const patientIds = caregiver.patients.map(id => id.toString());
    if (!patientIds.includes(patientId)) {
      return res.status(403).json({ error: 'You do not have access to this patient.' });
    }

    next();
  } catch (err) {
    next(err);
  }
};

/**
 * Ensure user can only access their own data (unless caregiver/admin)
 */
const ownDataOnly = (req, res, next) => {
  const requestedUserId = req.params.userId || req.body.userId;
  if (requestedUserId && requestedUserId !== req.user.id.toString()) {
    if (!['caregiver', 'admin'].includes(req.user.role)) {
      return res.status(403).json({ error: 'Access denied to other user data.' });
    }
  }
  next();
};

module.exports = { protect, authorize, verifyCaregiverAccess, ownDataOnly };
