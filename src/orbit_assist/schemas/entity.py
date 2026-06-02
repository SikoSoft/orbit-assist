from datetime import date
from enum import Enum
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field

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
    optionsOnly: bool
    options: list[str] | None = None
    # defaultValue: any

EntityPropertyCalculationOperation = Literal["*", "+", "-", "/"]

class EntityPropertyCalculationReference(BaseModel):
    propertyConfigId: int

class EntityPropertyCalculation(BaseModel):
    value1: EntityPropertyCalculationReference | float
    value2: EntityPropertyCalculationReference | float
    operation: EntityPropertyCalculationOperation

class EntityCalculatedPropertyConfig(BaseModel):
    entityConfigId: int
    id: int
    userId: str
    name: str
    prefix: str
    suffix: str
    hidden: bool
    dataType: str
    calculation: EntityPropertyCalculation

class EntityConfig(BaseModel):
    id: int
    userId: str
    name: str
    description: str | None = None
    properties: list[EntityCalculatedPropertyConfig | EntityPropertyConfig]
    aiEnabled: bool
    aiIdentifyPrompt: str | None = None

class EntityConfigResponse(BaseModel):
    entityConfigs: list[EntityConfig]

class PropertyImageValue(BaseModel):
    src: str
    alt: str

class CreateEntityProperty(BaseModel):
    id: int | None = None
    propertyConfigId: int
    value: str | int | float | bool | date | PropertyImageValue
    order: int


class CreateEntityRequest(BaseModel):
    entityConfigId: int
    userId: str | None = None
    properties: list[CreateEntityProperty]
    propertyReferences: list[dict[str, str | int | float | bool | date | PropertyImageValue]] | None = None
    tags: list[str] | None = None
    timeZone: int | None = None
    published: bool = False
    suggested: bool = False
    identified: bool = False
    createdAt: str | None = None

class EntityProperty(BaseModel):
    id: int
    propertyConfigId: int
    value: str | int | float | bool | date | PropertyImageValue
    order: int

class Entity(BaseModel):
  id: int
  type: int
  createdAt: str
  updatedAt: str
  tags: list[str]
  properties: list[EntityProperty]

class ImageUploadResponse(BaseModel):
    filename: str
    size: int
    content_type: str
    entity: Entity

class SuggestEntityResponse(BaseModel):
    entity: list[Entity]

class SuggestedProperty(BaseModel):
    propertyConfigId: int
    value: str | int | float | bool

class EntitySuggestion(BaseModel):
    type: int
    userId: str
    properties: list[SuggestedProperty]
    hour: int
    minute: int

class EntityAnalysisResponse(BaseModel):
    suggestions: list[EntitySuggestion]


class ListFilterType(str, Enum):
    CONTAINS_ONE_OF = "containsOneOf"
    CONTAINS_ALL_OF = "containsAllOf"


class ListFilterTimeType(str, Enum):
    ALL_TIME = "allTime"
    EXACT_DATE = "exactDate"
    RANGE = "range"


class AllTimeContext(BaseModel):
    type: Literal[ListFilterTimeType.ALL_TIME]


class ExactDateContext(BaseModel):
    type: Literal[ListFilterTimeType.EXACT_DATE]
    date: str


class RangeContext(BaseModel):
    type: Literal[ListFilterTimeType.RANGE]
    start: str
    end: str


TimeContext = Annotated[
    Union[AllTimeContext, ExactDateContext, RangeContext],
    Field(discriminator="type"),
]


class TextType(str, Enum):
    CONTAINS = "contains"
    STARTS_WITH = "startsWith"
    ENDS_WITH = "endsWith"
    EQUALS = "equals"


class TextContext(BaseModel):
    type: TextType
    subStr: str


TaggingContext = dict[ListFilterType, list[str]]


class FilterProperty(BaseModel):
    propertyId: int
    value: str | int | float | bool | date | PropertyImageValue
    operation: TextType


class ListFilter(BaseModel):
    tagging: TaggingContext
    includeUntagged: bool
    includeAll: bool
    includeAllTagging: bool
    includeTypes: list[int]
    time: TimeContext
    properties: list[FilterProperty]


class ListConfig(BaseModel):
    id: str
    filter: ListFilter | None = None
