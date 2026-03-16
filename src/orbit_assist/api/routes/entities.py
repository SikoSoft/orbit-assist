import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from orbit_assist.api.deps import get_authorization_header

logger = logging.getLogger(__name__)
router = APIRouter(tags=["entities"])


@router.get("/entities")
async def get_entities(request: Request, token: str = Depends(get_authorization_header)):
    logger.info("Fetching entities")
    response = await request.app.state.orbit_client.get(
        "/entity",
        headers={"authorization": token},
    )
    if response.status_code != 200:
        logger.error("Failed to fetch entities: %s", response.text)
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entities")
    return response.json()
