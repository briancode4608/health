# 🏥 Chronic Health & Lifestyle Platform

A full-stack backend + AI microservice platform for chronic disease patients, providing intelligent meal/exercise recommendations, symptom pattern detection, computer vision food scanning, and caregiver dashboards.

---

## Architecture

```
Frontend (React)
      │
      ▼
Node.js API (Express)          ← Auth, CRUD, business logic
      │
      ├── MongoDB (Mongoose)   ← Persistent storage
      │
      └── Python AI Service (FastAPI)
                │
                ├── Meal Recommender      (Random Forest + rule engine)
                ├── Exercise Recommender  (Gradient Boosting + safety caps)
                ├── Food Scanner          (OpenCV + SVM classifier)
                └── Health Insights       (IsolationForest + trend analysis)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Server | Node.js 20 + Express 4 |
| Database | MongoDB 7 + Mongoose 7 |
| Authentication | JWT + bcrypt |
| AI Service | Python 3.11 + FastAPI |
| ML Models | scikit-learn (RF, GBT, SVM, IsolationForest) |
| Computer Vision | OpenCV + color/texture feature extraction |
| Containerisation | Docker + Docker Compose |

---

## Project Structure

```
chronic-health-platform/
├── backend/
│   ├── src/
│   │   ├── app.js                  # Express entry point
│   │   ├── config/
│   │   │   ├── db.js               # MongoDB connection
│   │   │   └── logger.js           # Winston logger
│   │   ├── models/
│   │   │   ├── User.js             # User + BMI virtual + bcrypt hooks
│   │   │   ├── MealLog.js          # Food items + nutrition summary
│   │   │   ├── ExerciseLog.js      # MET-based calorie estimation
│   │   │   ├── HealthLog.js        # Vitals + wellness score virtual
│   │   │   └── Routine.js          # Daily routine reminders
│   │   ├── controllers/
│   │   │   ├── authController.js
│   │   │   ├── mealController.js
│   │   │   ├── exerciseController.js
│   │   │   ├── healthLogController.js
│   │   │   ├── routineController.js
│   │   │   ├── caregiverController.js
│   │   │   └── aiController.js     # Multer + AI proxy
│   │   ├── middleware/
│   │   │   ├── auth.js             # JWT protect, authorize, caregiver access
│   │   │   ├── validation.js       # express-validator rules
│   │   │   └── errorHandler.js     # Centralised error handling
│   │   ├── routes/
│   │   │   ├── auth.js
│   │   │   ├── meals.js
│   │   │   ├── exercise.js
│   │   │   ├── healthLogs.js
│   │   │   ├── routines.js
│   │   │   ├── caregiver.js
│   │   │   └── ai.js
│   │   └── services/
│   │       └── aiService.js        # Axios client with retry logic
│   ├── tests/
│   │   ├── auth.test.js
│   │   └── logs.test.js
│   ├── Dockerfile
│   └── package.json
│
├── ai-service/
│   ├── main.py                     # FastAPI app + lifespan model loader
│   ├── models/
│   │   └── schemas.py              # All Pydantic request/response schemas
│   ├── routers/
│   │   ├── meals.py
│   │   ├── exercise.py
│   │   ├── food_scan.py
│   │   └── insights.py
│   ├── services/
│   │   ├── model_loader.py         # Train/cache all ML models
│   │   ├── meal_service.py         # RF + condition rule engine
│   │   ├── exercise_service.py     # GBT + safety intensity caps
│   │   ├── food_service.py         # OpenCV + SVM food classifier
│   │   └── insights_service.py     # Trend, anomaly, correlation analysis
│   ├── tests/
│   │   └── test_services.py        # pytest async tests
│   ├── Dockerfile
│   ├── requirements.txt
│   └── pytest.ini
│
├── docker-compose.yml
├── mongo-init.js
└── README.md
```

---

## Quick Start

### Option A — Docker Compose (Recommended)

```bash
# 1. Clone and enter the project
cd chronic-health-platform

# 2. Copy and configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your JWT_SECRET

# 3. Launch all services
docker compose up --build

# Services will be available at:
#   API:        http://localhost:5000
#   AI Service: http://localhost:8000
#   Mongo:      mongodb://localhost:27017
```

### Option B — Local Development

**Backend (Node.js)**
```bash
cd backend
npm install
cp .env.example .env   # edit .env
npm run dev            # nodemon hot-reload
```

**AI Service (Python)**
```bash
cd ai-service
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**MongoDB**
```bash
# Via Docker (simplest)
docker run -d -p 27017:27017 --name mongo mongo:7.0
```

---

## API Reference

### Authentication

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/auth/register` | Public | Register user or caregiver |
| POST | `/api/auth/login` | Public | Login, receive JWT |
| GET | `/api/auth/me` | Bearer | Get current user profile |
| PUT | `/api/auth/profile` | Bearer | Update profile |

**Register payload:**
```json
{
  "name": "Jane Doe",
  "email": "jane@example.com",
  "password": "Secure123",
  "role": "user",
  "age": 45,
  "weight": 72,
  "height": 165,
  "conditions": ["diabetes", "hypertension"],
  "dietaryRestrictions": ["gluten-free"],
  "activityLevel": "lightly_active"
}
```

---

### Meal APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/meals/recommendations` | AI meal plan for today |
| POST | `/api/meals/log` | Log a meal |
| GET | `/api/meals/history` | Paginated meal history + daily summary |
| DELETE | `/api/meals/:id` | Delete a meal log |

**Log meal payload:**
```json
{
  "foodItems": [
    { "name": "Brown Rice", "portion": "150g", "calories": 195, "protein": 4, "carbs": 42, "fat": 1.5 }
  ],
  "mealType": "lunch",
  "date": "2024-01-15T12:30:00Z"
}
```

---

### Exercise APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/exercise/recommendations` | AI exercise plan (energy + condition aware) |
| POST | `/api/exercise/log` | Log an exercise session |
| GET | `/api/exercise/history` | History + weekly stats |

---

### Health Logs

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/logs` | Create daily health log |
| GET | `/api/logs` | Get logs + 14-day trend analytics |
| GET | `/api/logs/:id` | Single log |
| PUT | `/api/logs/:id` | Update log |

**Health log payload:**
```json
{
  "mood": 7,
  "energyLevel": 6,
  "sleepHours": 7.5,
  "sleepQuality": 8,
  "symptoms": [{ "name": "joint pain", "severity": 5, "duration": "3 hours" }],
  "painLevel": 5,
  "stressLevel": 4,
  "bloodPressure": { "systolic": 128, "diastolic": 82 },
  "bloodGlucose": { "value": 110, "unit": "mg/dL", "takenWhen": "fasting" }
}
```

---

### Routine APIs

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/routine` | List all active routines |
| POST | `/api/routine` | Create routine |
| PUT | `/api/routine/:id` | Update routine |
| DELETE | `/api/routine/:id` | Delete routine |

---

### AI APIs (Node proxy → Python FastAPI)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ai/food-scan` | Upload food image → nutrition data |
| POST | `/api/ai/health-insights` | Generate health insights from logs |
| POST | `/api/ai/meal-recommendations` | Meal recommendations (custom payload) |
| POST | `/api/ai/exercise-recommendations` | Exercise recommendations |

**Food scan:** `multipart/form-data` with field `image` (JPEG/PNG/WebP, max 5MB)

---

### Caregiver Dashboard APIs

Requires role: `caregiver` or `admin`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/patients` | List assigned patients with alert levels |
| POST | `/api/patients/assign` | Assign patient by email |
| GET | `/api/patient/:id/logs` | Full log history (health + meals + exercise) |
| GET | `/api/patient/:id/insights` | AI insights for patient |

---

## ML Models

### 1. Meal Recommender (Random Forest)
- **Features:** age, BMI, activity level, number of conditions, is_diabetic, is_hypertensive, is_celiac, is_vegan, is_vegetarian
- **Target:** calorie category (low / medium / high)
- **Post-processing:** condition rule engine filters unsafe meals, applies dietary restrictions

### 2. Exercise Recommender (Gradient Boosting)
- **Features:** energy level, pain level, age, activity level, number of conditions, average past duration, is_cardiac, is_arthritis
- **Target:** intensity level (very_light / light / moderate / vigorous)
- **Safety layer:** condition-based intensity caps (cardiac → max light; high pain → very_light)

### 3. Food Classifier (SVM + OpenCV)
- **Features:** 56-dim HSV colour histogram + 8-dim Sobel texture = 64 total
- **Classes:** 16 food categories (rice, chicken, salad, pizza, etc.)
- **Fallback:** dominant colour heuristic if model unavailable
- **Production upgrade path:** Replace SVM with MobileNetV2 fine-tuned on Food-101

### 4. Health Insights Engine
- **Trend detection:** linear regression slope on mood / energy / sleep sequences
- **Anomaly detection:** Z-score (n<10) or IsolationForest (n≥10) on energy values
- **Symptom mining:** frequency counting + co-occurrence pattern detection
- **Correlations:** Pearson r for sleep↔mood and exercise↔energy

---

## Security

- **JWT** tokens (HS256, configurable expiry)
- **bcrypt** password hashing (12 rounds)
- **Role-based access**: user / caregiver / admin
- **Caregiver isolation**: caregivers only see assigned patients
- **Rate limiting**: 100 req/15min globally, 10 req/15min on auth routes
- **Input validation**: express-validator on all endpoints
- **Helmet**: HTTP security headers
- **File upload**: type + size validation, temp-file cleanup after processing

---

## Running Tests

**Backend (Jest):**
```bash
cd backend
npm test               # run all tests with coverage
npm test -- --watch    # watch mode
```

**AI Service (pytest):**
```bash
cd ai-service
pytest tests/ -v                    # all tests
pytest tests/ -v -k "meal"         # only meal tests
pytest tests/ -v --tb=long         # verbose tracebacks
```

---

## Environment Variables

```env
# backend/.env
PORT=5000
NODE_ENV=development
MONGO_URI=mongodb://localhost:27017/chronic_health_db
JWT_SECRET=your_secret_here_min_32_chars
JWT_EXPIRES_IN=7d
AI_SERVICE_URL=http://localhost:8000
BCRYPT_ROUNDS=12
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX=100
```

---

## Production Checklist

- [ ] Set strong `JWT_SECRET` (32+ random chars)
- [ ] Enable MongoDB authentication
- [ ] Configure HTTPS / TLS termination (nginx/load balancer)
- [ ] Set `NODE_ENV=production`
- [ ] Replace synthetic ML training data with real patient data
- [ ] Upgrade food classifier to MobileNetV2 + Food-101 fine-tuning
- [ ] Add refresh token rotation
- [ ] Configure log aggregation (ELK / CloudWatch)
- [ ] Set up database backups
- [ ] Add HIPAA/GDPR data handling (encryption at rest, audit logs)
