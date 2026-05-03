import logging
import json
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from google.genai import types, errors as genai_errors
from orbit_assist.schemas.entity import EntityAnalysisResponse, EntityConfig, EntityConfigResponse, ListConfig, ListFilter, ListFilterTimeType, RangeContext
from orbit_assist.api.deps import get_authorization_header

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


def _keep_property(value) -> bool:
    return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))


def _filter_entity_properties(entities: list) -> list:
    result = []
    for entity in entities:
        filtered = [
            p for p in entity.get("properties", [])
            if _keep_property(p.get("value"))
        ]
        result.append({**entity, "properties": filtered})
    return result


def _build_prompt(entities: list) -> str:
    filtered = _filter_entity_properties(entities)
    lines = [
        "You are an assistant for a user of a activity tracking management platform called Orbit. Your job is to review the items created in the past week and identify any commonly added entries, and the approximate hour window in which they typically occur. You should only identify entities that you are confident are present in the content.",
        "Two entries are considered the same if they share identical propertyConfigId and value pairs across all non-date properties. Treat any entries that differ only in date-typed properties as matches.",
        "",
        "Past weeks entries:",
    ]
    lines.append(json.dumps(filtered, indent=2))
    return "\n".join(lines)



async def _fetch_list_config(orbit_client, token: str, list_config_id: int) -> ListConfig:
    response = await orbit_client.get(f"/listConfig/{list_config_id}", headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch list config")
    return ListConfig.model_validate(response.json())


def _apply_time_range_filter(list_filter: ListFilter) -> ListFilter:
    now = datetime.now()
    week_ago = now - timedelta(weeks=1)
    fmt = "%Y-%m-%dT%H:%M"
    return list_filter.model_copy(update={
        "time": RangeContext(
            type=ListFilterTimeType.RANGE,
            start=week_ago.strftime(fmt),
            end=now.strftime(fmt),
        )
    })


async def _fetch_entities(orbit_client, token: str, list_filter: ListFilter):
    filter_encoded = urllib.parse.quote(list_filter.model_dump_json())
    response = await orbit_client.get(f"/entity?filter={filter_encoded}", headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entities")
    return response.json()


@router.get("/assist/suggestEntity", response_model=EntityAnalysisResponse)
async def suggest_entity(
    request: Request,
    list_config_id: str = Query(..., alias="listConfigId"),
    token: str = Depends(get_authorization_header),
) -> EntityAnalysisResponse:
    list_config = await _fetch_list_config(request.app.state.orbit_client, token, list_config_id)
    if list_config.filter:
        entity_filter = _apply_time_range_filter(list_config.filter)
        entities = await _fetch_entities(request.app.state.orbit_client, token, entity_filter)

        logger.info("Fetched entities: %s", entities)
        print("Entities:", entities)


    prompt = _build_prompt(entities)
    logger.debug("Prompt: %s", prompt.replace("\n", "\\n"))

    try:
        genai_response = await request.app.state.genai_client.aio.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=[prompt],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=EntityAnalysisResponse,
            ),
        )
    except genai_errors.APIError as e:
        logger.error("Gemini API failed: %s - %s", e.code, e.message, exc_info=True)
        raise HTTPException(status_code=502, detail="Gemini API error")

    logger.info("Gemini response: %s", genai_response.text)

    return EntityAnalysisResponse.model_validate_json(genai_response.text)
