import logging
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from pydantic import BaseModel
from google.genai import types

from orbit_assist.api.deps import get_authorization_header
from orbit_assist.schemas.prompt import PromptResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


class ImageUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str

def handle_record(album_name: str, artist: str):
    """Triggered when a record is detected."""
    print(f"Executing record logic for: {album_name}. {artist}")

def handle_food(name: str, portion_size: str):
    """Triggered when a food item is detected."""
    print(f"Executing food logic for: {name} in {portion_size} portion")

tools = [handle_record, handle_food]

@router.post("/assist/entity", response_model=ImageUploadResponse)
async def upload_image(request: Request,token: str = Depends(get_authorization_header), file: UploadFile = File(...)) -> ImageUploadResponse:
    try:
        allowed_types = {"image/jpeg", "image/png", "image/gif", "image/webp"}
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}"
            )
        
        max_size = 5 * 1024 * 1024
        image_contents = await file.read()
        if len(image_contents) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Max size: {max_size / 1024 / 1024}MB"
            )
        
        logger.info(f"Uploaded image: {file.filename}, size: {len(image_contents)}, token: {token}")
        
        try:
            response = await request.app.state.genai_client.aio.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=[types.Part.from_bytes(data=image_contents, mime_type="image/jpeg"), f"Analyze the uploaded image and identify any entities. If a record is detected, provide the album name and artist. If a food item is detected, provide the name and portion size. Use the following tools to handle the identified entities: {tools}"],
                config=types.GenerateContentConfig(tools=tools)
            )

            for call in response.candidates[0].content.parts:
                    if call.function_call:
                        fn_name = call.function_call.name
                        args = call.function_call.args
                        
                        funcs = {f.__name__: f for f in tools}
                        funcs[fn_name](**args)


        except Exception:
            logger.exception("Prompt handling failed")
            raise HTTPException(status_code=500, detail="Failed to process prompt")
        
        return ImageUploadResponse(
            filename=file.filename,
            size=len(image_contents),
            content_type=file.content_type,
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Image upload failed")
        raise HTTPException(status_code=500, detail="Failed to process image")