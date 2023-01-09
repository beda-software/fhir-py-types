from dataclasses import dataclass
from typing import List, Optional


@dataclass
class StructurePropertyType:
    code: str
    required: bool
    isarray: bool
    target_profile: Optional[List[str]]


@dataclass
class StructureDefinition:
    id: str
    docstring: str
    type: Optional[List[StructurePropertyType]]
    elements: dict[str, "StructureDefinition"]
