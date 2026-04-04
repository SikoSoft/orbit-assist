import logging
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File
from google.genai import types, errors as genai_errors
from orbit_assist.schemas.entity import EntityConfig, EntityConfigResponse, EntityResponse, ImageUploadResponse
from orbit_assist.api.deps import get_authorization_header

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])

_ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

_DATA_TYPE_MAP = {
    "text": "STRING",
    "string": "STRING",
    "number": "NUMBER",
    "float": "NUMBER",
    "integer": "INTEGER",
    "int": "INTEGER",
    "boolean": "BOOLEAN",
    "bool": "BOOLEAN",
}

_COERCE_MAP = {
    "INTEGER": int,
    "NUMBER": float,
    "BOOLEAN": bool,
}


def _get_property_config_id_by_name(entity_config: EntityConfig, prop_name: str) -> int:
    for prop in entity_config.properties:
        if prop.name.lower() == prop_name.lower():
            return prop.id
    raise ValueError(f"Property '{prop_name}' not found in entity config '{entity_config.name}'")


def _get_property_config_id_by_type(entity_config: EntityConfig, prop_type: str) -> int:
    for prop in entity_config.properties:
        if prop.dataType.lower() == prop_type.lower():
            return prop.id
    raise ValueError(f"Property of type '{prop_type}' not found in entity config '{entity_config.name}'")


def _build_function_declarations(configs: list[EntityConfig]) -> list[types.FunctionDeclaration]:
    declarations = []
    for config in configs:
        if not config.aiEnabled:
            continue
        visible_props = [p for p in config.properties if not p.hidden]
        properties = {
            "entityConfigId": types.Schema(
                type="INTEGER",
                description=f"The entity config ID. Always use {config.id}.",
            ),
            **{
                prop.name: types.Schema(
                    type=_DATA_TYPE_MAP.get(prop.dataType.lower(), "STRING"),
                    description=prop.name,
                )
                for prop in visible_props
            },
        }
        required = ["entityConfigId"] + [prop.name for prop in visible_props if prop.required]
        declarations.append(types.FunctionDeclaration(
            name=f"handle_{config.name.lower().replace(' ', '_').replace('-', '_')}",
            description=config.description or f"Called when a {config.name} is identified in the image",
            parameters=types.Schema(
                type="OBJECT",
                properties=properties,
                required=required or None,
            ),
        ))
    return declarations


def _build_prompt(configs: list[EntityConfig]) -> str:
    lines = [
        "Analyze the uploaded image and identify any entities present.",
        "Call the single handler function that best matches what you see.",
        "",
        "Available entity types:",
    ]
    custom_prompt_lines = []
    for config in configs:
        if not config.aiEnabled:
            continue
        visible_props = [p for p in config.properties if not p.hidden]
        prop_list = ", ".join(
            f"{p.name} (id: {p.id}, {'required' if p.required else 'optional'})"
            for p in visible_props
        )
        lines.append(f"  - {config.name} (id: {config.id}): {config.description}. Properties: {prop_list}")
        if config.aiIdentifyPrompt:
            custom_prompt_lines.append(f" - {config.aiIdentifyPrompt}")

    if custom_prompt_lines:
        lines.append("")
        lines.append("Additional instructions:")
        lines.extend(custom_prompt_lines)
    return "\n".join(lines)


def _coerce_value(value, prop_data_type: str):
    schema_type = _DATA_TYPE_MAP.get(prop_data_type.lower(), "STRING")
    coerce = _COERCE_MAP.get(schema_type)
    return coerce(value) if coerce is not None else value


def _build_entity_payload(function_call, configs: list[EntityConfig], image_url: str | None) -> dict:
    entity_config_id = int(function_call.args.get("entityConfigId"))
    matching_config = next((c for c in configs if c.id == entity_config_id), None)

    prop_config_by_name = {prop.name.lower(): prop for prop in matching_config.properties}
    property_config_ids = {
        prop_name: _get_property_config_id_by_name(matching_config, prop_name)
        for prop_name in function_call.args
        if prop_name != "entityConfigId"
    }
    properties = [
        {
            "propertyConfigId": prop_config_id,
            "value": _coerce_value(
                function_call.args[prop_name],
                prop_config_by_name[prop_name.lower()].dataType,
            ),
        }
        for prop_name, prop_config_id in property_config_ids.items()
    ]

    if matching_config is not None:
        try:
            image_config_id = _get_property_config_id_by_type(matching_config, "image")
            properties.append({"propertyConfigId": image_config_id, "value": {"src": image_url, "alt": ""}})
        except Exception:
            logger.info("No image property found in config")

    return {"entityConfigId": entity_config_id, "properties": properties, "tags": []}


async def _fetch_configs(orbit_client, token: str) -> list[EntityConfig]:
    response = await orbit_client.get("/entityConfig", headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to fetch entity config")
    configs = EntityConfigResponse.model_validate(response.json())
    logger.info("Fetched %d entity configs: %s", len(configs.entityConfigs), [c.name for c in configs.entityConfigs])
    return configs.entityConfigs


async def _validate_file(file: UploadFile) -> bytes:
    if file.content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(_ALLOWED_IMAGE_TYPES)}")
    contents = await file.read()
    if len(contents) > _MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Max size: {_MAX_FILE_SIZE / 1024 / 1024:.0f}MB")
    return contents


async def _create_entity(orbit_client, token: str, payload: dict) -> EntityResponse:
    response = await orbit_client.post("/entity", json=payload, headers={"authorization": token})
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail="Failed to create entity")
    logger.info("Created entity: %d %s", response.status_code, response.text)
    return EntityResponse.model_validate(response.json())


@router.post("/assist/entity", response_model=ImageUploadResponse)
async def upload_image(
    request: Request,
    token: str = Depends(get_authorization_header),
    file: UploadFile = File(...),
) -> ImageUploadResponse:
    configs = await _fetch_configs(request.app.state.orbit_client, token)
    image_contents = await _validate_file(file)

    declarations = _build_function_declarations(configs)
    prompt = _build_prompt(configs)
    logger.info("Generated %d function declarations: %s", len(declarations), [d.name for d in declarations])
    logger.debug("Prompt: %s", prompt.replace("\n", "\\n"))

    try:
        genai_response = await request.app.state.genai_client.aio.models.generate_content(
            model="models/gemini-3.1-flash-lite-preview",
            contents=[
                types.Part.from_bytes(data=image_contents, mime_type=file.content_type),
                prompt,
            ],
            config=types.GenerateContentConfig(tools=[types.Tool(function_declarations=declarations)])
        )
    except genai_errors.APIError as e:
        logger.error("Gemini API failed: %s - %s", e.code, e.message, exc_info=True)
        raise HTTPException(status_code=502, detail="Gemini API error")

    for part in genai_response.candidates[0].content.parts:
        if part.function_call:
            payload = _build_entity_payload(part.function_call, configs, request.query_params.get("url"))
            logger.info("Entity payload — handler: %s, payload: %s", part.function_call.name, payload)
            entity = await _create_entity(request.app.state.orbit_client, token, payload)
            return ImageUploadResponse(
                filename=file.filename,
                size=len(image_contents),
                content_type=file.content_type,
                entity=entity,
            )

    raise HTTPException(status_code=422, detail="Gemini did not identify any entity in the image")
