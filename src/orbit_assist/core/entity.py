import logging
from datetime import datetime, timedelta
from typing import Any
from fastapi import HTTPException
from orbit_assist.schemas.entity import (
    CreateEntityProperty, CreateEntityRequest, Entity, EntityConfig,
    EntityConfigResponse, PropertyImageValue,
)

logger = logging.getLogger(__name__)


def get_date_in_time_zone(date_str: str, time_zone: int) -> datetime:
    # time_zone uses JS getTimezoneOffset() convention: negative for east (-120 for UTC+2)
    # server_tz uses Python utcoffset() convention: positive for east (+120 for UTC+2)
    # Step 1: server local → UTC: subtract server_tz
    # Step 2: UTC → client local: subtract time_zone (e.g. -(-120) = +120 for UTC+2)
    server_tz = int(datetime.now().astimezone().utcoffset().total_seconds() / 60)
    return datetime.fromisoformat(date_str) - timedelta(minutes=server_tz + time_zone)


def _get_property_config_id_by_type(entity_config: EntityConfig, prop_type: str) -> int:
    for prop in entity_config.properties:
        if prop.dataType.lower() == prop_type.lower():
            return prop.id
    raise ValueError(f"Property of type '{prop_type}' not found in entity config '{entity_config.name}'")


async def fetch_configs(orbit_client, token: str) -> list[EntityConfig]:
    response = await orbit_client.get("/entityConfig", headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entity config")
    configs = EntityConfigResponse.model_validate(response.json())
    logger.debug("Fetched entity configs response: %s", configs)
    logger.info("Fetched %d entity configs: %s", len(configs.entityConfigs), [c.name for c in configs.entityConfigs])
    return configs.entityConfigs


def build_entity_payload(
    entity_config_id: int,
    property_values: dict[int, Any],
    configs: list[EntityConfig],
    image_url: str | None = None,
    time_zone: int | None = None,
    published: bool = True,
    suggestion: bool = False,
    user_id: str | None = None,
) -> CreateEntityRequest:
    logger.info("Building entity payload for config ID %d with properties: %s", entity_config_id, property_values)
    matching_config = next((c for c in configs if c.id == entity_config_id), None)
    if matching_config is None:
        raise HTTPException(status_code=422, detail=f"No entity config found for id {entity_config_id}")
    prop_order_by_id = {prop.id: i for i, prop in enumerate(matching_config.properties)}

    properties = [
        CreateEntityProperty(
            propertyConfigId=prop_config_id,
            value=value,
            order=prop_order_by_id.get(prop_config_id, 0),
        )
        for prop_config_id, value in property_values.items()
    ]

    for prop in matching_config.properties:
        if prop.name.lower() == "occurred at":
            date_str = datetime.now().strftime("%Y-%m-%dT%H:%M")
            if time_zone is not None:
                date_str = get_date_in_time_zone(date_str, time_zone).strftime("%Y-%m-%dT%H:%M")
            properties.append(CreateEntityProperty(
                propertyConfigId=prop.id,
                value=date_str,
                order=prop_order_by_id[prop.id],
            ))
            break

    if image_url:
        try:
            image_config_id = _get_property_config_id_by_type(matching_config, "image")
            properties.append(CreateEntityProperty(
                propertyConfigId=image_config_id,
                value=PropertyImageValue(src=image_url, alt=""),
                order=prop_order_by_id[image_config_id],
            ))
        except Exception:
            logger.info("No image property found in config")

    return CreateEntityRequest(
        entityConfigId=entity_config_id,
        userId=user_id,
        properties=properties,
        tags=[],
        timeZone=time_zone,
        suggestion=suggestion,
        published=published,
    )


async def create_entity(orbit_client, token: str, payload: CreateEntityRequest) -> Entity:
    response = await orbit_client.post(
        "/entity",
        json=payload.model_dump(exclude={"suggestion"}, exclude_none=True),
        headers={"authorization": token},
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to create entity")
    logger.info("Created entity: %d %s", response.status_code, response.text)
    return Entity.model_validate(response.json())
