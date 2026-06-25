const request = require('supertest');
const mongoose = require('mongoose');
const app = require('../src/app');
const User = require('../src/models/User');
const MealLog = require('../src/models/MealLog');
const HealthLog = require('../src/models/HealthLog');

let token;
let userId;

beforeAll(async () => {
  await mongoose.connect(process.env.MONGO_URI_TEST || 'mongodb://localhost:27017/chronic_health_test_2');
  const res = await request(app).post('/api/auth/register').send({
    name: 'Log Tester', email: 'logger@example.com',
    password: 'Logger1234', conditions: ['diabetes']
  });
  token = res.body.token;
  userId = res.body.user._id;
});

afterAll(async () => {
  await mongoose.connection.dropDatabase();
  await mongoose.connection.close();
});

// ── Health Logs ──────────────────────────────────────────────────────────────

describe('POST /api/logs', () => {
  it('should create a health log', async () => {
    const res = await request(app)
      .post('/api/logs')
      .set('Authorization', `Bearer ${token}`)
      .send({
        mood: 7,
        energyLevel: 6,
        sleepHours: 7.5,
        symptoms: [{ name: 'headache', severity: 4 }],
        painLevel: 3
      });

    expect(res.statusCode).toBe(201);
    expect(res.body.log).toHaveProperty('mood', 7);
    expect(res.body.log.symptoms).toHaveLength(1);
  });

  it('should reject log with invalid mood', async () => {
    const res = await request(app)
      .post('/api/logs')
      .set('Authorization', `Bearer ${token}`)
      .send({ mood: 15, energyLevel: 5, sleepHours: 7 });

    expect(res.statusCode).toBe(400);
  });

  it('should require authentication', async () => {
    const res = await request(app)
      .post('/api/logs')
      .send({ mood: 5, energyLevel: 5, sleepHours: 7 });

    expect(res.statusCode).toBe(401);
  });
});

describe('GET /api/logs', () => {
  beforeEach(async () => {
    await HealthLog.deleteMany({ userId });
    // Seed some logs
    const logs = Array.from({ length: 5 }, (_, i) => ({
      userId,
      mood: 5 + i % 3,
      energyLevel: 4 + i % 4,
      sleepHours: 6 + i * 0.5,
      symptoms: [],
      date: new Date(Date.now() - i * 24 * 60 * 60 * 1000)
    }));
    await HealthLog.insertMany(logs);
  });

  it('should return paginated health logs', async () => {
    const res = await request(app)
      .get('/api/logs?page=1&limit=3')
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    expect(res.body.logs).toHaveLength(3);
    expect(res.body.pagination.total).toBe(5);
  });

  it('should filter by date range', async () => {
    const today = new Date().toISOString().split('T')[0];
    const res = await request(app)
      .get(`/api/logs?startDate=${today}`)
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    expect(res.body.logs.length).toBeGreaterThanOrEqual(1);
  });
});

// ── Meal Logs ────────────────────────────────────────────────────────────────

describe('POST /api/meals/log', () => {
  it('should log a meal successfully', async () => {
    const res = await request(app)
      .post('/api/meals/log')
      .set('Authorization', `Bearer ${token}`)
      .send({
        foodItems: [{ name: 'Oatmeal', calories: 350, protein: 12, carbs: 58, fat: 6 }],
        mealType: 'breakfast'
      });

    expect(res.statusCode).toBe(201);
    expect(res.body.meal.mealType).toBe('breakfast');
    expect(res.body.meal.calories).toBe(350);
  });

  it('should auto-calculate calories from food items if not provided', async () => {
    const res = await request(app)
      .post('/api/meals/log')
      .set('Authorization', `Bearer ${token}`)
      .send({
        foodItems: [
          { name: 'Rice', calories: 200 },
          { name: 'Chicken', calories: 180 }
        ],
        mealType: 'lunch'
      });

    expect(res.statusCode).toBe(201);
    expect(res.body.meal.calories).toBe(380);
  });

  it('should reject meal without food items', async () => {
    const res = await request(app)
      .post('/api/meals/log')
      .set('Authorization', `Bearer ${token}`)
      .send({ foodItems: [], mealType: 'lunch' });

    expect(res.statusCode).toBe(400);
  });
});

describe('GET /api/meals/history', () => {
  beforeEach(async () => {
    await MealLog.deleteMany({ userId });
    await MealLog.insertMany([
      { userId, foodItems: [{ name: 'Toast', calories: 150 }], mealType: 'breakfast', calories: 150 },
      { userId, foodItems: [{ name: 'Salad', calories: 200 }], mealType: 'lunch', calories: 200 },
      { userId, foodItems: [{ name: 'Pasta', calories: 450 }], mealType: 'dinner', calories: 450 },
    ]);
  });

  it('should return meal history', async () => {
    const res = await request(app)
      .get('/api/meals/history')
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    expect(res.body.meals.length).toBeGreaterThanOrEqual(3);
  });

  it('should filter by meal type', async () => {
    const res = await request(app)
      .get('/api/meals/history?mealType=breakfast')
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    res.body.meals.forEach(m => expect(m.mealType).toBe('breakfast'));
  });
});

// ── Routines ─────────────────────────────────────────────────────────────────

describe('Routine CRUD', () => {
  let routineId;

  it('POST /api/routine - should create a routine', async () => {
    const res = await request(app)
      .post('/api/routine')
      .set('Authorization', `Bearer ${token}`)
      .send({
        title: 'Morning Medication',
        time: '08:00',
        activityType: 'medication',
        description: 'Take metformin 500mg',
        reminderEnabled: true
      });

    expect(res.statusCode).toBe(201);
    expect(res.body.routine.title).toBe('Morning Medication');
    routineId = res.body.routine._id;
  });

  it('GET /api/routine - should list routines', async () => {
    const res = await request(app)
      .get('/api/routine')
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    expect(Array.isArray(res.body.routines)).toBe(true);
  });

  it('PUT /api/routine/:id - should update a routine', async () => {
    const createRes = await request(app)
      .post('/api/routine')
      .set('Authorization', `Bearer ${token}`)
      .send({ title: 'Walk', time: '09:00', activityType: 'exercise' });
    const id = createRes.body.routine._id;

    const res = await request(app)
      .put(`/api/routine/${id}`)
      .set('Authorization', `Bearer ${token}`)
      .send({ title: 'Morning Walk', reminderEnabled: false });

    expect(res.statusCode).toBe(200);
    expect(res.body.routine.title).toBe('Morning Walk');
  });

  it('DELETE /api/routine/:id - should delete a routine', async () => {
    const createRes = await request(app)
      .post('/api/routine')
      .set('Authorization', `Bearer ${token}`)
      .send({ title: 'Delete Me', time: '10:00', activityType: 'custom' });
    const id = createRes.body.routine._id;

    const res = await request(app)
      .delete(`/api/routine/${id}`)
      .set('Authorization', `Bearer ${token}`);

    expect(res.statusCode).toBe(200);
    expect(res.body.message).toMatch(/deleted/i);
  });
});
