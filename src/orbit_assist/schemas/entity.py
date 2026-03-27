from pydantic import BaseModel

class EntityPropertyConfig(BaseModel):
    entityConfigId: int
    id: int
    userId: str
    name: str
    required: int
    repeat: int
    allowed: int
    prefix: str
    suffix: str
    hidden: bool
    dataType: str
    # defaultValue: any

class EntityConfig(BaseModel):
    id: int
    userId: str
    name: str
    description: str
    properties: list[EntityPropertyConfig]

class EntityConfigResponse(BaseModel):
    entityConfigs: list[EntityConfig]

class PropertyImageValue(BaseModel):
    src: str
    alt: str

class CreateEntityProperty(BaseModel):
    id: int
    propertyConfigId: int
    value: str | int | float | bool | PropertyImageValue
    order: int


class CreateEntityRequest(BaseModel):
    entityConfigId: int
    properties: list[CreateEntityProperty]
    propertyReferences: list[dict[str, str | int | float | bool]] | None = None
    tags: list[str] | None = None
    timeZone: int | None = None