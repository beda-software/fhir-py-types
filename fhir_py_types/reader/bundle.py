import json
import logging
import os

from typing import Any, Iterable, List, Optional, Tuple

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)

FHIR_TO_SYSTEM_TYPE_MAP = {
    "System.String": "str",
    "System.Boolean": "bool",
    "System.Time": "str",
    "System.Date": "str",
    "System.DateTime": "str",
    "System.Decimal": "int",
    "System.Integer": "int",
}

logger = logging.getLogger(__name__)


DefinitionsBundle = dict[str, Any]


def parse_type_identifier(type_: str) -> str:
    code = type_.split("/")[-1]
    return FHIR_TO_SYSTEM_TYPE_MAP.get(code, code)


def parse_target_profile(target_profile: List[str]) -> List[str]:
    profiles = [p.split("/")[-2:] for p in target_profile]
    if any(type_ != "StructureDefinition" for type_, _ in profiles):
        raise ValueError(f"Unknown target profile type: {target_profile}")
    return [profile for _, profile in profiles]


def parse_resource_name(path: str) -> str:
    uppercamelcase = lambda s: s[:1].upper() + s[1:]

    return "".join(uppercamelcase(p) for p in path.removeprefix("#").split("."))


def unwrap_schema_type(
    schema: dict, kind: Optional[StructureDefinitionKind]
) -> Iterable[Tuple[str, List[str]]]:
    match kind:
        case StructureDefinitionKind.COMPLEX | StructureDefinitionKind.RESOURCE:
            return [(parse_resource_name(schema["base"]["path"]), [])]
        case _:
            if "contentReference" in schema:
                return [(parse_resource_name(schema["contentReference"]), [])]
            else:
                return ((t["code"], t.get("targetProfile", [])) for t in schema["type"])


def parse_property_type(
    schema: dict, kind: Optional[StructureDefinitionKind]
) -> List[StructurePropertyType]:
    return [
        StructurePropertyType(
            code=parse_type_identifier(type_),
            target_profile=parse_target_profile(target_profile),
            required=schema["min"] != 0,
            isarray=schema["max"] != "1",
        )
        for type_, target_profile in unwrap_schema_type(schema, kind)
    ]


def parse_property_key(schema: dict) -> str:
    property_key: str = schema["id"].split(".")[-1]
    # 'Choice of Types' are handled by property type, will not parse suffix
    return property_key.removesuffix("[x]")


def parse_property_kind(schema: dict):
    match schema.get("type"):
        case [{"code": "BackboneElement"}] | [{"code": "Element"}]:
            return StructureDefinitionKind.COMPLEX
        case _:
            return None


def parse_base_structure_definition(definition: dict[str, Any]) -> StructureDefinition:
    kind = StructureDefinitionKind.from_str(definition["kind"])
    schemas = definition["snapshot"]["element"]

    match kind:
        case StructureDefinitionKind.PRIMITIVE:
            schema = next(
                s for s in schemas if s["id"] == definition["type"] + ".value"
            )
        case _:
            schema = next(s for s in schemas if s["id"] == definition["type"])

    return StructureDefinition(
        id=definition["id"],
        kind=kind,
        docstring=schema["definition"],
        type=parse_property_type(schema, kind),
        elements={},
    )


def parse_structure_definition(definition: dict[str, Any]) -> StructureDefinition:
    structure_definition = parse_base_structure_definition(definition)
    schemas = (
        e for e in definition["snapshot"]["element"] if e["id"] != definition["type"]
    )

    for schema in sorted(schemas, key=lambda s: len(s["path"])):
        subtree = structure_definition
        for path_component in schema["path"].split(".")[1:-1]:
            subtree = subtree.elements[path_component]

        property_key = parse_property_key(schema)
        property_kind = parse_property_kind(schema)

        subtree.elements[property_key] = StructureDefinition(
            id=parse_resource_name(schema["id"]),
            docstring=schema["definition"],
            type=parse_property_type(schema, property_kind),
            kind=property_kind,
            elements={},
        )

    return structure_definition


def select_structure_definition_resources(bundle: DefinitionsBundle):
    return (
        e["resource"]
        for e in bundle["entry"]
        if "resource" in e and e["resource"]["resourceType"] == "StructureDefinition"
    )


def read_structure_definitions(
    bundle: DefinitionsBundle,
) -> Iterable[StructureDefinition]:
    raw_definitions = select_structure_definition_resources(bundle)

    return (parse_structure_definition(definition) for definition in raw_definitions)


def load_from_bundle(path: str) -> Iterable[StructureDefinition]:
    with open(os.path.abspath(path), encoding="utf8") as schema_file:
        return read_structure_definitions(json.load(schema_file))
