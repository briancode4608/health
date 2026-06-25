const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../src/app');

// ── Test Setup ────────────────────────────────────────────────────────────────

beforeAll(async () => {
  await mongoose.connect(process.env.MONGO_URI || 'mongodb://localhost:27017/chronic_health_test');
});

afterAll(async () => {
  await mongoose.connection.dropDatabase();
  await mongoose.connection.close();
});

// ── Auth Tests ────────────────────────────────────────────────────────────────

describe('Authentication', () => {
  let authToken;
  const testUser = {
    name: 'Test Patient',
    email: `test_${Date.now()}@example.com`,
    password: 'TestPass123',
    age: 35,
    weight: 72,
    height: 175,
    conditions: ['diabetes type 2'],
    activityLevel: 'lightly_active'
  };

  test('POST /api/auth/register — creates new user', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send(testUser)
      .expect(201);

    expect(res.body).toHaveProperty('token');
    expect(res.body.user.email).toBe(testUser.email);
    expect(res.body.user).not.toHaveProperty('password');
    authToken = res.body.token;
  });

  test('POST /api/auth/register — rejects duplicate email', async () => {
    await request(app)
      .post('/api/auth/register')
      .send(testUser)
      .expect(400);
  });

  test('POST /api/auth/register — rejects weak password', async () => {
    await request(app)
      .post('/api/auth/register')
      .send({ ...testUser, email: 'other@test.com', password: 'weak' })
      .expect(400);
  });

  test('POST /api/auth/login — returns token on valid credentials', async () => {
    const res = await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email, password: testUser.password })
      .expect(200);

    expect(res.body).toHaveProperty('token');
    authToken = res.body.token;
  });

  test('POST /api/auth/login — rejects invalid password', async () => {
    await request(app)
      .post('/api/auth/login')
      .send({ email: testUser.email, password: 'wrongpass' })
      .expect(401);
  });

  test('GET /api/auth/me — returns user profile when authenticated', async () => {
    const res = await request(app)
      .get('/api/auth/me')
      .set('Authorization', `Bearer ${authToken}`)
      .expect(200);

    expect(res.body.user.email).toBe(testUser.email);
  });

  test('GET /api/auth/me — rejects unauthenticated request', async () => {
    await request(app).get('/api/auth/me').expect(401);
  });

  // Export token for subsequent test suites
  global.authToken = authToken;
  global.testUserEmail = testUser.email;
});

// ── Health Logs Tests ─────────────────────────────────────────────────────────

describe('Health Logs', () => {
  let token;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Log Tester',
        email: `log_${Date.now()}@test.com`,
        password: 'LogTest123',
      });
    token = res.body.token;
  });

  test('POST /api/logs — creates health log', async () => {
    const res = await request(app)
      .post('/api/logs')
      .set('Authorization', `Bearer ${token}`)
      .send({
        mood: 7,
        energyLevel: 6,
        sleepHours: 7.5,
        symptoms: [{ name: 'fatigue', severity: 4 }],
        stressLevel: 5
      })
      .expect(201);

    expect(res.body.log).toHaveProperty('_id');
    expect(res.body.log.mood).toBe(7);
    expect(res.body.log.symptoms).toHaveLength(1);
  });

  test('POST /api/logs — validates mood range', async () => {
    await request(app)
      .post('/api/logs')
      .set('Authorization', `Bearer ${token}`)
      .send({ mood: 15, energyLevel: 5, sleepHours: 8 })
      .expect(400);
  });

  test('GET /api/logs — returns logs with trends', async () => {
    const res = await request(app)
      .get('/api/logs')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body).toHaveProperty('logs');
    expect(res.body).toHaveProperty('trends');
    expect(Array.isArray(res.body.logs)).toBe(true);
  });

  test('GET /api/logs — supports date filtering', async () => {
    const res = await request(app)
      .get('/api/logs?startDate=2024-01-01&endDate=2099-01-01')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(Array.isArray(res.body.logs)).toBe(true);
  });
});

// ── Meal Logs Tests ───────────────────────────────────────────────────────────

describe('Meal Logs', () => {
  let token;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Meal Tester',
        email: `meal_${Date.now()}@test.com`,
        password: 'MealTest123',
      });
    token = res.body.token;
  });

  test('POST /api/meals/log — logs a meal', async () => {
    const res = await request(app)
      .post('/api/meals/log')
      .set('Authorization', `Bearer ${token}`)
      .send({
        mealType: 'breakfast',
        foodItems: [
          { name: 'Oatmeal', calories: 300, protein: 10, carbs: 50, fat: 5 },
          { name: 'Banana', calories: 90, protein: 1, carbs: 23, fat: 0.3 }
        ]
      })
      .expect(201);

    expect(res.body.meal).toHaveProperty('_id');
    expect(res.body.meal.mealType).toBe('breakfast');
    expect(res.body.meal.calories).toBe(390);
  });

  test('POST /api/meals/log — rejects empty food items', async () => {
    await request(app)
      .post('/api/meals/log')
      .set('Authorization', `Bearer ${token}`)
      .send({ mealType: 'lunch', foodItems: [] })
      .expect(400);
  });

  test('GET /api/meals/history — returns paginated meal history', async () => {
    const res = await request(app)
      .get('/api/meals/history?page=1&limit=10')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body).toHaveProperty('meals');
    expect(res.body).toHaveProperty('pagination');
    expect(res.body).toHaveProperty('dailySummary');
  });
});

// ── Exercise Logs Tests ───────────────────────────────────────────────────────

describe('Exercise Logs', () => {
  let token;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Exercise Tester',
        email: `ex_${Date.now()}@test.com`,
        password: 'ExTest123!',
      });
    token = res.body.token;
  });

  test('POST /api/exercise/log — logs exercise session', async () => {
    const res = await request(app)
      .post('/api/exercise/log')
      .set('Authorization', `Bearer ${token}`)
      .send({
        exerciseType: 'walking',
        duration: 30,
        intensity: 'light'
      })
      .expect(201);

    expect(res.body.log).toHaveProperty('_id');
    expect(res.body.log.exerciseType).toBe('walking');
    expect(res.body.log.caloriesBurned).toBeGreaterThan(0);
  });

  test('POST /api/exercise/log — validates duration bounds', async () => {
    await request(app)
      .post('/api/exercise/log')
      .set('Authorization', `Bearer ${token}`)
      .send({ exerciseType: 'running', duration: 0, intensity: 'vigorous' })
      .expect(400);
  });

  test('GET /api/exercise/history — returns logs with weekly stats', async () => {
    const res = await request(app)
      .get('/api/exercise/history')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body).toHaveProperty('logs');
    expect(res.body).toHaveProperty('weeklyStats');
  });
});

// ── Routine Tests ─────────────────────────────────────────────────────────────

describe('Routines', () => {
  let token, routineId;

  beforeAll(async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Routine Tester',
        email: `routine_${Date.now()}@test.com`,
        password: 'RoutTest123',
      });
    token = res.body.token;
  });

  test('POST /api/routine — creates routine', async () => {
    const res = await request(app)
      .post('/api/routine')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: 'Morning Medication',
        time: '08:00',
        activityType: 'medication',
        description: 'Take metformin 500mg',
        reminderEnabled: true
      })
      .expect(201);

    expect(res.body.routine).toHaveProperty('_id');
    expect(res.body.routine.title).toBe('Morning Medication');
    routineId = res.body.routine._id;
  });

  test('GET /api/routine — returns all routines', async () => {
    const res = await request(app)
      .get('/api/routine')
      .set('Authorization', `Bearer ${token}`)
      .expect(200);

    expect(res.body).toHaveProperty('routines');
    expect(Array.isArray(res.body.routines)).toBe(true);
  });

  test('PUT /api/routine/:id — updates routine', async () => {
    const res = await request(app)
      .put(`/api/routine/${routineId}`)
      .set('Authorization', `Bearer ${token}`)
      .send({ description: 'Take metformin 1000mg after breakfast' })
      .expect(200);

    expect(res.body.routine.description).toContain('1000mg');
  });

  test('DELETE /api/routine/:id — deletes routine', async () => {
    await request(app)
      .delete(`/api/routine/${routineId}`)
      .set('Authorization', `Bearer ${token}`)
      .expect(200);
  });

  test('DELETE /api/routine/:id — returns 404 after deletion', async () => {
    await request(app)
      .delete(`/api/routine/${routineId}`)
      .set('Authorization', `Bearer ${token}`)
      .expect(404);
  });
});

// ── Caregiver Tests ───────────────────────────────────────────────────────────

describe('Caregiver Access Control', () => {
  let patientToken, caregiverToken;

  beforeAll(async () => {
    const patientRes = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Test Patient',
        email: `patient_${Date.now()}@test.com`,
        password: 'Patient123',
        role: 'user'
      });
    patientToken = patientRes.body.token;

    const caregiverRes = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Test Caregiver',
        email: `caregiver_${Date.now()}@test.com`,
        password: 'Caregiver123',
        role: 'caregiver'
      });
    caregiverToken = caregiverRes.body.token;
  });

  test('GET /api/patients — accessible to caregiver', async () => {
    await request(app)
      .get('/api/patients')
      .set('Authorization', `Bearer ${caregiverToken}`)
      .expect(200);
  });

  test('GET /api/patients — blocked for regular user', async () => {
    await request(app)
      .get('/api/patients')
      .set('Authorization', `Bearer ${patientToken}`)
      .expect(403);
  });

  test('GET /api/patients — blocked without auth', async () => {
    await request(app)
      .get('/api/patients')
      .expect(401);
  });
});

// ── Security Tests ────────────────────────────────────────────────────────────

describe('Security', () => {
  test('GET /health — public health check endpoint works', async () => {
    const res = await request(app).get('/health').expect(200);
    expect(res.body.status).toBe('ok');
  });

  test('Invalid JSON body returns 400', async () => {
    await request(app)
      .post('/api/auth/login')
      .set('Content-Type', 'application/json')
      .send('{ invalid json }')
      .expect(400);
  });

  test('Invalid ObjectId returns 400', async () => {
    const res = await request(app)
      .post('/api/auth/register')
      .send({
        name: 'Sec Tester',
        email: `sec_${Date.now()}@test.com`,
        password: 'SecTest123',
      });
    const token = res.body.token;

    await request(app)
      .get('/api/logs/not-a-valid-id')
      .set('Authorization', `Bearer ${token}`)
      .expect(400);
  });

  test('Unknown route returns 404', async () => {
    await request(app).get('/api/nonexistent').expect(404);
  });
});
