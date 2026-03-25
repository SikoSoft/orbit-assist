import logging
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


class ImageUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str


@router.post("/assist/entity", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    try:
        # Validate file type
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        
        # Validate file size (e.g., max 5MB)
        max_size = 5 * 1024 * 1024
        contents = await file.read()
        if len(contents) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {max_size / 1024 / 1024}MB"
            )
        
        # Process the file (save, store reference, etc.)
        logger.info(f"Uploaded image: {file.filename}, size: {len(contents)}")
        
        # Here you could:
        # - Save to disk: with open(f"uploads/{file.filename}", "wb") as f: f.write(contents)
        # - Save to database
        # - Send to cloud storage
        # - Pass to ML model, etc.
        
        return ImageUploadResponse(
            filename=file.filename,
            size=len(contents),
            content_type=file.content_type,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image upload failed")
        raise HTTPException(status_code=500, detail="Failed to process image")