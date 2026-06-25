from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import uvicorn
import time

from routers import meals, exercise, food_scan, insights
from services.model_loader import ModelLoader

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load ML models on startup, release on shutdown."""
    logger.info("🔬 Loading ML models...")
    await ModelLoader.initialize()
    logger.info("✅ AI microservice ready")
    yield
    logger.info("Shutting down AI microservice...")
    ModelLoader.cleanup()

app = FastAPI(
    title="Chronic Health AI Microservice",
    description="ML-powered health recommendations, food recognition, and insights",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time() - start)*1000:.1f}ms"
    return response

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal AI service error", "detail": str(exc)}
    )

# Health check
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "chronic-health-ai",
        "models_loaded": ModelLoader.is_ready()
    }

# Mount routers
app.include_router(meals.router, prefix="/ai", tags=["Meal Recommendations"])
app.include_router(exercise.router, prefix="/ai", tags=["Exercise Recommendations"])
app.include_router(food_scan.router, prefix="/ai", tags=["Food Recognition"])
app.include_router(insights.router, prefix="/ai", tags=["Health Insights"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
