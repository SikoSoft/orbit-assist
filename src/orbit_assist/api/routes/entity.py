import logging
from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from pydantic import BaseModel
from psycopg import errors as pg_errors
from google.genai import types, errors as genai_errors
from orbit_assist.schemas.entity import EntityConfig, EntityConfigResponse, EntityResponse

from orbit_assist.api.deps import get_authorization_header

logger = logging.getLogger(__name__)
router = APIRouter(tags=["images"])


class ImageUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    entity: EntityResponse


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
        visible_props = [p for p in config.properties if not p.hidden]
        prop_list = ", ".join(
            f"{p.name} (id: {p.id}, {'required' if p.required else 'optional'})"
            for p in visible_props
        )
        if (config.aiEnabled):
            lines.append(f"  - {config.name} (id: {config.id}): {config.description}. Properties: {prop_list}")
        if (config.aiEnabled and config.aiIdentifyPrompt):
            custom_prompt_lines.append(f" - {config.aiIdentifyPrompt}")

    if custom_prompt_lines:
        lines.append("")
        lines.append("Additional instructions:")
        lines.extend(custom_prompt_lines)
    return "\n".join(lines)


@router.post("/assist/entity", response_model=ImageUploadResponse)
async def upload_image(request: Request, token: str = Depends(get_authorization_header), file: UploadFile = File(...)) -> ImageUploadResponse:
    try:
        config_response = await request.app.state.orbit_client.get(
            "/entityConfig",
            headers={"authorization": token},
        )

        if config_response.status_code != 200:
            raise HTTPException(status_code=config_response.status_code, detail="Failed to fetch entity config")

        configs = EntityConfigResponse.model_validate(config_response.json())
        logger.info("Fetched %d entity configs: %s", len(configs.entityConfigs), [c.name for c in configs.entityConfigs])

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

        declarations = _build_function_declarations(configs.entityConfigs)
        prompt = _build_prompt(configs.entityConfigs)
        logger.info("Generated %d function declarations for Gemini: %s", len(declarations), [d.name for d in declarations])
        logger.debug("Generated prompt for Gemini: %s", prompt.replace("\n", "\\n"))

        try:
            genai_response = await request.app.state.genai_client.aio.models.generate_content(
                model="models/gemini-3.1-flash-lite-preview",
                contents=[
                    types.Part.from_bytes(data=image_contents, mime_type=file.content_type),
                    prompt,
                ],
                config=types.GenerateContentConfig(tools=[types.Tool(function_declarations=declarations)])
            )

            for part in genai_response.candidates[0].content.parts:
                if part.function_call:
                    entity_config_id = int(part.function_call.args.get("entityConfigId"))
                    matching_config = next((c for c in configs.entityConfigs if c.id == entity_config_id), None)
                    property_config_ids = {
                        prop_name: _get_property_config_id_by_name(matching_config, prop_name)
                        for prop_name in part.function_call.args
                        if prop_name != "entityConfigId"
                    }
                    properties_payload = [
                        {"propertyConfigId": prop_config_id, "value": part.function_call.args[prop_name]}
                        for prop_name, prop_config_id in property_config_ids.items()
                    ]

                    if matching_config is not None:
                        try: 
                            image_config_id = _get_property_config_id_by_type(matching_config, "image")
                            # image_config = next((p for p in matching_config.properties if p.dataType.lower() == "image"), None)
                            if image_config_id is not None:
                                properties_payload.append({"propertyConfigId": image_config_id, "value": {"src": request.query_params.get("url"), "alt": ""}})                            
                        except Exception:
                            logger.info("Failed to find image property config")
                            image_config = None
                    logger.info("Entity payload — handler: %s, payload: %s", part.function_call.name, properties_payload)

                    entity_payload = {
                        "entityConfigId": entity_config_id,
                        "properties": properties_payload,
                        "tags": [],
                    }

                    create_response = await request.app.state.orbit_client.post(
                        "/entity",
                        json=entity_payload,
                        headers={"authorization": token},
                    )

                    if create_response.status_code != 200:
                        raise HTTPException(status_code=create_response.status_code, detail="Failed to create entity")
                    
                    entity = EntityResponse.model_validate(create_response.json())
                    logger.info("Create entity response: %d %s", create_response.status_code, create_response.text)


        except genai_errors.APIError as e:
            # This captures the full error and puts it in ONE log entry
            logging.error(f"Gemini API failed: {e.code} - {e.message}", exc_info=True)
            # You can also return a cleaner error to your frontend here
            raise


        except Exception:
            logger.exception("Gemini processing failed")
            raise HTTPException(status_code=500, detail="Failed to process image with Gemini")

        return ImageUploadResponse(
            filename=file.filename,
            size=len(image_contents),
            content_type=file.content_type,
            entity=entity
        )

    except HTTPException:
        raise
    except Exception:
        logger.exception("Image upload failed")
        raise HTTPException(status_code=500, detail="Failed to process image")