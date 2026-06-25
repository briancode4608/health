const User = require('../models/User');
const HealthLog = require('../models/HealthLog');
const MealLog = require('../models/MealLog');
const ExerciseLog = require('../models/ExerciseLog');
const aiService = require('../services/aiService');

/**
 * @route   GET /api/patients
 * @access  Private (caregiver, admin)
 */
const getPatients = async (req, res, next) => {
  try {
    let patients;

    if (req.user.role === 'admin') {
      patients = await User.find({ role: 'user', isActive: true })
        .select('-password')
        .lean();
    } else {
      const caregiver = await User.findById(req.user.id)
        .populate('patients', '-password');
      patients = caregiver.patients;
    }

    // Enrich with latest vitals
    const enriched = await Promise.all(patients.map(async (patient) => {
      const latestLog = await HealthLog.findOne({ userId: patient._id })
        .sort({ date: -1 })
        .select('mood energyLevel symptoms sleepHours painLevel date')
        .lean();

      return {
        ...patient,
        latestVitals: latestLog || null,
        alertLevel: computeAlertLevel(latestLog)
      };
    }));

    res.json({ patients: enriched, count: enriched.length });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   POST /api/patients/assign
 * @access  Private (caregiver)
 */
const assignPatient = async (req, res, next) => {
  try {
    const { patientEmail } = req.body;

    const patient = await User.findOne({ email: patientEmail, role: 'user' });
    if (!patient) {
      return res.status(404).json({ error: 'Patient not found.' });
    }

    // Prevent duplicate assignment
    const caregiver = await User.findById(req.user.id);
    if (caregiver.patients.includes(patient._id)) {
      return res.status(400).json({ error: 'Patient already assigned.' });
    }

    await User.findByIdAndUpdate(req.user.id, {
      $push: { patients: patient._id }
    });
    await User.findByIdAndUpdate(patient._id, {
      caregiver: req.user.id
    });

    res.json({ message: `Patient ${patient.name} assigned successfully.` });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/patient/:id/logs
 * @access  Private (caregiver, admin)
 */
const getPatientLogs = async (req, res, next) => {
  try {
    const patientId = req.params.id;
    const { days = 30 } = req.query;

    const since = new Date(Date.now() - parseInt(days) * 24 * 60 * 60 * 1000);

    const [patient, healthLogs, mealLogs, exerciseLogs] = await Promise.all([
      User.findById(patientId).select('-password').lean(),
      HealthLog.find({ userId: patientId, date: { $gte: since } })
        .sort({ date: -1 }).lean(),
      MealLog.find({ userId: patientId, date: { $gte: since } })
        .sort({ date: -1 }).lean(),
      ExerciseLog.find({ userId: patientId, date: { $gte: since } })
        .sort({ date: -1 }).lean()
    ]);

    if (!patient) {
      return res.status(404).json({ error: 'Patient not found.' });
    }

    // Symptom frequency analysis
    const symptomFrequency = {};
    healthLogs.forEach(log => {
      log.symptoms.forEach(s => {
        if (!symptomFrequency[s.name]) {
          symptomFrequency[s.name] = { count: 0, avgSeverity: 0, severities: [] };
        }
        symptomFrequency[s.name].count++;
        symptomFrequency[s.name].severities.push(s.severity);
      });
    });
    Object.keys(symptomFrequency).forEach(name => {
      const s = symptomFrequency[name];
      s.avgSeverity = parseFloat((s.severities.reduce((a, b) => a + b, 0) / s.severities.length).toFixed(1));
      delete s.severities;
    });

    res.json({
      patient,
      summary: {
        period: `${days} days`,
        healthLogCount: healthLogs.length,
        mealLogCount: mealLogs.length,
        exerciseLogCount: exerciseLogs.length,
        avgMood: average(healthLogs.map(l => l.mood)),
        avgEnergy: average(healthLogs.map(l => l.energyLevel)),
        avgSleep: average(healthLogs.map(l => l.sleepHours)),
        symptomFrequency
      },
      healthLogs,
      mealLogs,
      exerciseLogs
    });
  } catch (err) {
    next(err);
  }
};

/**
 * @route   GET /api/patient/:id/insights
 * @access  Private (caregiver, admin)
 */
const getPatientInsights = async (req, res, next) => {
  try {
    const patientId = req.params.id;
    const patient = await User.findById(patientId).select('-password').lean();
    if (!patient) return res.status(404).json({ error: 'Patient not found.' });

    const insights = await aiService.generateHealthInsights(patientId);

    res.json({
      patient: { id: patient._id, name: patient.name, conditions: patient.conditions },
      insights,
      generatedAt: new Date().toISOString()
    });
  } catch (err) {
    next(err);
  }
};

// Helper: compute alert level based on latest vitals
function computeAlertLevel(log) {
  if (!log) return 'unknown';
  const highSeveritySymptoms = log.symptoms?.filter(s => s.severity >= 7).length || 0;
  if (log.mood <= 3 || log.energyLevel <= 2 || highSeveritySymptoms > 0 || (log.painLevel && log.painLevel >= 7)) {
    return 'high';
  }
  if (log.mood <= 5 || log.energyLevel <= 4 || log.sleepHours < 5) {
    return 'medium';
  }
  return 'low';
}

function average(arr) {
  const valid = arr.filter(v => v != null);
  if (!valid.length) return null;
  return parseFloat((valid.reduce((a, b) => a + b, 0) / valid.length).toFixed(1));
}

module.exports = { getPatients, assignPatient, getPatientLogs, getPatientInsights };
