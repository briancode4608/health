const Routine = require('../models/Routine');

/**
 * @route   GET /api/routine
 * @access  Private
 */
const getRoutines = async (req, res, next) => {
  try {
    const routines = await Routine.find({
      userId: req.user.id,
      isActive: true
    }).sort({ time: 1 }).lean();

    // Group by activity type
    const grouped = routines.reduce((acc, r) => {
      const key = r.activityType;
      if (!acc[key]) acc[key] = [];
      acc[key].push(r);
      return acc;
    }, {});

    res.json({ routines, grouped, count: routines.length });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/routine
 * @access  Private
 */
const createRoutine = async (req, res, next) => {
  try {
    const { title, time, activityType, description, reminderEnabled, frequency, customDays, color } = req.body;

    const routine = await Routine.create({
      userId: req.user.id,
      title, time, activityType, description,
      reminderEnabled: reminderEnabled !== false,
      frequency: frequency || 'daily',
      customDays: customDays || [],
      color
    });

    res.status(201).json({ message: 'Routine created.', routine });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   PUT /api/routine/:id
 * @access  Private
 */
const updateRoutine = async (req, res, next) => {
  try {
    const allowedFields = ['title', 'time', 'activityType', 'description',
      'reminderEnabled', 'frequency', 'customDays', 'isActive', 'color'];
    const updates = {};
    allowedFields.forEach(f => { if (req.body[f] !== undefined) updates[f] = req.body[f]; });

    const routine = await Routine.findOneAndUpdate(
      { _id: req.params.id, userId: req.user.id },
      updates,
      { new: true, runValidators: true }
    );

    if (!routine) return res.status(404).json({ error: 'Routine not found.' });

    res.json({ message: 'Routine updated.', routine });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   DELETE /api/routine/:id
 * @access  Private
 */
const deleteRoutine = async (req, res, next) => {
  try {
    const routine = await Routine.findOneAndDelete({
      _id: req.params.id,
      userId: req.user.id
    });

    if (!routine) return res.status(404).json({ error: 'Routine not found.' });

    res.json({ message: 'Routine deleted.' });
  } catch (err) {
    next(err);
  }
};

module.exports = { getRoutines, createRoutine, updateRoutine, deleteRoutine };
