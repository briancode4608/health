const HealthLog = require('../models/HealthLog');
const aiService = require('../services/aiService');

/**
 * @route   POST /api/logs
 * @access  Private
 */
const createLog = async (req, res, next) => {
  try {
    const {
      mood, energyLevel, symptoms, sleepHours, sleepQuality,
      stressLevel, painLevel, bloodPressure, bloodGlucose, medications, notes, date
    } = req.body;

    const log = await HealthLog.create({
      userId: req.user.id,
      mood, energyLevel, symptoms: symptoms || [],
      sleepHours, sleepQuality, stressLevel, painLevel,
      bloodPressure, bloodGlucose, medications: medications || [],
      notes, date: date || new Date()
    });

    // Trigger background insight generation (non-blocking)
    aiService.generateHealthInsights(req.user.id).catch(() => {});

    res.status(201).json({ message: 'Health log created.', log });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/logs
 * @access  Private
 */
const getLogs = async (req, res, next) => {
  try {
    const { startDate, endDate, page = 1, limit = 30 } = req.query;

    const filter = { userId: req.user.id };
    if (startDate || endDate) {
      filter.date = {};
      if (startDate) filter.date.$gte = new Date(startDate);
      if (endDate) filter.date.$lte = new Date(endDate);
    }

    const skip = (parseInt(page) - 1) * parseInt(limit);
    const [logs, total] = await Promise.all([
      HealthLog.find(filter).sort({ date: -1 }).skip(skip).limit(parseInt(limit)).lean(),
      HealthLog.countDocuments(filter)
    ]);

    // Trend analytics (last 14 days)
    const twoWeeksAgo = new Date(Date.now() - 14 * 24 * 60 * 60 * 1000);
    const trends = await HealthLog.aggregate([
      { $match: { userId: req.user.id, date: { $gte: twoWeeksAgo } } },
      {
        $group: {
          _id: { $dateToString: { format: '%Y-%m-%d', date: '$date' } },
          avgMood: { $avg: '$mood' },
          avgEnergy: { $avg: '$energyLevel' },
          avgSleep: { $avg: '$sleepHours' },
          avgPain: { $avg: '$painLevel' },
          symptomCount: { $sum: { $size: '$symptoms' } }
        }
      },
      { $sort: { _id: 1 } }
    ]);

    res.json({
      logs,
      pagination: {
        page: parseInt(page), limit: parseInt(limit), total,
        pages: Math.ceil(total / parseInt(limit))
      },
      trends
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/logs/:id
 * @access  Private
 */
const getLog = async (req, res, next) => {
  try {
    const log = await HealthLog.findOne({ _id: req.params.id, userId: req.user.id });
    if (!log) return res.status(404).json({ error: 'Health log not found.' });
    res.json({ log });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   PUT /api/logs/:id
 * @access  Private
 */
const updateLog = async (req, res, next) => {
  try {
    const allowedUpdates = [
      'mood', 'energyLevel', 'symptoms', 'sleepHours', 'sleepQuality',
      'stressLevel', 'painLevel', 'bloodPressure', 'bloodGlucose', 'medications', 'notes'
    ];
    const updates = {};
    allowedUpdates.forEach(f => { if (req.body[f] !== undefined) updates[f] = req.body[f]; });

    const log = await HealthLog.findOneAndUpdate(
      { _id: req.params.id, userId: req.user.id },
      updates,
      { new: true, runValidators: true }
    );
    if (!log) return res.status(404).json({ error: 'Health log not found.' });

    res.json({ message: 'Health log updated.', log });
  } catch (err) {
    next(err);
  }
};

module.exports = { createLog, getLogs, getLog, updateLog };
