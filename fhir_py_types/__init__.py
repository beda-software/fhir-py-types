from dataclasses import dataclass
from enum import Enum
from typing import List, Literal, Optional


class StructureDefinitionKind(Enum):
    PRIMITIVE = "primitive-type"
    COMPLEX = "complex-type"
    CAPABILITY = "capability"
    OPERATION = "operation"
    RESOURCE = "resource"

    @staticmethod
    def from_str(kind):
        match kind:
            case "primitive-type":
                return StructureDefinitionKind.PRIMITIVE
            case "complex-type":
                return StructureDefinitionKind.COMPLEX
            case "capability":
                return StructureDefinitionKind.CAPABILITY
            case "operation":
                return StructureDefinitionKind.OPERATION
            case "resource":
                return StructureDefinitionKind.RESOURCE
            case _:
                raise ValueError(f"Unknown StructureDefinition kind: {kind}")


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
    kind: Optional[
        Literal[
            StructureDefinitionKind.PRIMITIVE,
            StructureDefinitionKind.COMPLEX,
            StructureDefinitionKind.CAPABILITY,
            StructureDefinitionKind.OPERATION,
            StructureDefinitionKind.RESOURCE,
        ]
    ] = None
