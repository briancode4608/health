/**
 * Shared utility functions for Chronic Health Platform backend
 */

/**
 * Build a MongoDB date-range filter from query params
 * @param {string|undefined} startDate
 * @param {string|undefined} endDate
 * @returns {object} Mongoose date filter or empty object
 */
const buildDateFilter = (startDate, endDate) => {
  if (!startDate && !endDate) return {};
  const filter = {};
  if (startDate) filter.$gte = new Date(startDate);
  if (endDate) filter.$lte = new Date(endDate);
  return { date: filter };
};

/**
 * Paginate a Mongoose query
 * @param {number} page  - 1-based page number
 * @param {number} limit - items per page (max 100)
 * @returns {{ skip: number, limit: number }}
 */
const getPagination = (page = 1, limit = 20) => {
  const safePage  = Math.max(1, parseInt(page));
  const safeLimit = Math.min(100, Math.max(1, parseInt(limit)));
  return { skip: (safePage - 1) * safeLimit, limit: safeLimit };
};

/**
 * Format a pagination response envelope
 * @param {number} page
 * @param {number} limit
 * @param {number} total
 */
const paginationMeta = (page, limit, total) => ({
  page: parseInt(page),
  limit: parseInt(limit),
  total,
  pages: Math.ceil(total / parseInt(limit)),
  hasNextPage: parseInt(page) < Math.ceil(total / parseInt(limit)),
  hasPrevPage: parseInt(page) > 1
});

/**
 * Compute simple arithmetic mean, ignoring nulls
 * @param {(number|null|undefined)[]} values
 * @returns {number|null}
 */
const safeMean = (values) => {
  const valid = values.filter(v => v != null && !isNaN(v));
  if (!valid.length) return null;
  return parseFloat((valid.reduce((a, b) => a + b, 0) / valid.length).toFixed(1));
};

/**
 * Map activityLevel string to a numeric MET multiplier
 */
const ACTIVITY_MET_MULTIPLIERS = {
  sedentary:         1.2,
  lightly_active:    1.375,
  moderately_active: 1.55,
  very_active:       1.725,
  extremely_active:  1.9
};

/**
 * Estimate daily calorie need using Mifflin-St Jeor equation
 * @param {{ age, weight, height, gender, activityLevel }} profile
 * @returns {number} estimated TDEE (kcal/day)
 */
const estimateDailyCalories = ({ age, weight, height, gender = 'other', activityLevel = 'sedentary' }) => {
  if (!age || !weight || !height) return 2000; // default
  // BMR (Mifflin-St Jeor)
  let bmr;
  if (gender === 'male') {
    bmr = 10 * weight + 6.25 * height - 5 * age + 5;
  } else if (gender === 'female') {
    bmr = 10 * weight + 6.25 * height - 5 * age - 161;
  } else {
    // Average of male and female
    bmr = 10 * weight + 6.25 * height - 5 * age - 78;
  }
  const multiplier = ACTIVITY_MET_MULTIPLIERS[activityLevel] || 1.2;
  return Math.round(bmr * multiplier);
};

/**
 * Sanitise a string to prevent NoSQL injection patterns
 * (express-validator handles most cases; this is a belt-and-suspenders helper)
 */
const sanitiseString = (str) => {
  if (typeof str !== 'string') return str;
  return str.replace(/[${}]/g, '').trim();
};

/**
 * Convert ISO date string to YYYY-MM-DD label
 */
const toDateLabel = (isoString) => {
  return new Date(isoString).toISOString().split('T')[0];
};

/**
 * Group an array of objects by a key-producing function
 * @param {any[]} arr
 * @param {function} keyFn
 * @returns {Object}
 */
const groupBy = (arr, keyFn) =>
  arr.reduce((acc, item) => {
    const key = keyFn(item);
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

module.exports = {
  buildDateFilter,
  getPagination,
  paginationMeta,
  safeMean,
  estimateDailyCalories,
  sanitiseString,
  toDateLabel,
  groupBy,
  ACTIVITY_MET_MULTIPLIERS
};
