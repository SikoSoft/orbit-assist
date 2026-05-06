import logging
import json
import urllib.parse
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from google.genai import types, errors as genai_errors
from orbit_assist.schemas.entity import EntityAnalysisResponse, EntityConfig, EntityConfigResponse, ListConfig, ListFilter, ListFilterTimeType, RangeContext
from orbit_assist.api.deps import get_authorization_header
from orbit_assist.core.entity import build_entity_payload, create_entity, fetch_configs

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


def _keep_property(value) -> bool:
    return isinstance(value, str) or (isinstance(value, int) and not isinstance(value, bool))


def _convert_timestamp(ts: str, offset_minutes: int) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (dt + timedelta(minutes=offset_minutes)).strftime("%Y-%m-%dT%H:%M:%S")


def _filter_entity_properties(entities: list, offset_minutes: int = 0) -> list:
    result = []
    for entity in entities:
        filtered = [
            {"propertyConfigId": p["propertyConfigId"], "value": p["value"]}
            for p in entity.get("properties", [])
            if _keep_property(p.get("value"))
        ]
        created_at = _convert_timestamp(entity["createdAt"], offset_minutes)
        result.append({"userId": entity.get("userId"), "createdAt": created_at, "type": entity.get("type"), "properties": filtered})
    return result


def _build_prompt(entities: list, offset_minutes: int = 0) -> str:
    filtered = _filter_entity_properties(entities, offset_minutes)
    lines = [
        "You are an assistant for a user of a activity tracking management platform called Orbit. Your job is to review the items created in the past week and identify any commonly added entries, and the average time (hour and minute) at which they are typically created. You should only identify entities that you are confident are present in the content.",
        "Two entries are considered the same if they share the same userId AND identical propertyConfigId and value pairs across all non-date properties. Treat any entries that differ only in date-typed properties as matches. Never group entries from different users together.",
        "For each identified suggestion, return the userId from the matching entries and determine the average hour and average minute across all matching entries.",
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
    response = await orbit_client.get(f"/entity?perPage=0&filter={filter_encoded}", headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entities")
    return response.json().get("entities", [])


async def _post_suggested_entities(orbit_client, token: str, payloads: list, date_str: str):
    body = [p.model_dump(exclude={"suggestion"}, exclude_none=True) for p in payloads]
    logger.info("Posting suggested entities to /suggestEntity/%s:\n%s", date_str, json.dumps(body, indent=2))
    response = await orbit_client.post(
        f"/suggestEntity/{date_str}",
        json=body,
        headers={"authorization": token},
    )
    if response.status_code == 409:
        logger.info("Suggested entities already exist for %s: %s", date_str, response.text)
    elif response.status_code != 200:
        logger.error("Failed to post suggested entities: %d %s", response.status_code, response.text)


@router.get("/assist/suggestEntity", response_model=EntityAnalysisResponse)
async def suggest_entity(
    request: Request,
    list_config_id: str = Query(..., alias="listConfigId"),
    timezone: str = Query("0"),
    token: str = Depends(get_authorization_header),
) -> EntityAnalysisResponse:
    offset_minutes = int(timezone)
    list_config = await _fetch_list_config(request.app.state.orbit_client, token, list_config_id)
    if list_config.filter:
        entity_filter = _apply_time_range_filter(list_config.filter)
        entities = await _fetch_entities(request.app.state.orbit_client, token, entity_filter)

        logger.info("Fetched entities:\n%s", json.dumps(entities, indent=2))

    prompt = _build_prompt(entities, offset_minutes)
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

    analysis = EntityAnalysisResponse.model_validate_json(genai_response.text)

    tomorrow = (datetime.now() + timedelta(days=1)).date()
    tomorrow_str = tomorrow.strftime("%Y-%m-%d")

    configs = await fetch_configs(request.app.state.orbit_client, token)
    payloads = []
    for suggestion_item in analysis.suggestions:
        property_values = {p.propertyConfigId: p.value for p in suggestion_item.properties}
        created_at = f"{tomorrow_str}T{suggestion_item.hour:02d}:{suggestion_item.minute:02d}:00"
        payload = build_entity_payload(
            suggestion_item.type,
            property_values,
            configs,
            suggestion=True,
            user_id=suggestion_item.userId,
        )
        payload.createdAt = created_at
        payloads.append(payload)

    await _post_suggested_entities(request.app.state.orbit_client, token, payloads, tomorrow_str)

    return analysis
