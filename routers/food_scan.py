import os
import tempfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from loguru import logger
from models.schemas import FoodScanResponse
from services.food_service import classify_food

router = APIRouter()

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


@router.post("/food-scan", response_model=FoodScanResponse)
async def scan_food_image(file: UploadFile = File(...)):
    """
    Detect food from an uploaded image using OpenCV feature extraction + SVM classifier.
    Returns detected food name, estimated calories, and full nutrition data.
    """
    # Validate content type
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{file.content_type}'. Allowed: JPEG, PNG, WebP."
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large. Maximum size is 5MB.")

    if len(contents) < 1000:
        raise HTTPException(status_code=400, detail="File too small to be a valid image.")

    # Write to temp file for OpenCV processing
    suffix = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ".jpg"
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        logger.info(f"Processing food image: {file.filename} ({len(contents)} bytes)")
        result = await classify_food(tmp_path)
        logger.info(f"Food detected: {result.detectedFood} (confidence={result.confidence:.2f})")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Food scan error: {e}")
        raise HTTPException(status_code=500, detail=f"Food recognition failed: {str(e)}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
