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