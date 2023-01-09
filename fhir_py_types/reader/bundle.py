import json
import keyword
import logging
import os

from typing import Any, Iterable, List, Optional

from fhir_py_types import StructureDefinition, StructurePropertyType

logger = logging.getLogger(__name__)


DefinitionsBundle = dict[str, Any]


def select_structure_definition_resources(bundle: DefinitionsBundle):
    return (
        e["resource"]
        for e in bundle["entry"]
        if "resource" in e and e["resource"]["resourceType"] == "StructureDefinition"
    )


def parse_target_profile(target_profile: List[str]) -> List[str]:
    profiles = [p.split("/")[-2:] for p in target_profile]
    if any(type_ != "StructureDefinition" for type_, _ in profiles):
        raise ValueError(f"Unknown target profile type: {target_profile}")
    return [profile for _, profile in profiles]


def parse_element_type(element: dict) -> Optional[List[StructurePropertyType]]:
    type_ = element.get("type")
    if type_ is not None:
        return [
            StructurePropertyType(
                code=category["code"].split("/")[-1],
                target_profile=parse_target_profile(category.get("targetProfile", [])),
                required=element["min"] != 0,
                isarray=element["max"] != "1",
            )
            for category in type_
        ]
    else:
        return None


def parse_element_id(element: dict) -> str:
    element_id: str = element["id"].split(".")[-1]
    if keyword.iskeyword(element_id):
        logger.warning(
            "In parsing '{}' id: '{}' is a keyword".format(element["id"], element_id)
        )
    # 'Choice of Data Types' are handled by property type, will not parse suffix
    return element_id.removesuffix("[x]")


def read_structure_definition(definition: dict[str, Any]) -> StructureDefinition:
    elements = definition["snapshot"]["element"]
    resource = next((e for e in elements if e["id"] == definition["type"]))
    elements = (e for e in elements if e["id"] != resource["id"])

    structure_definition = StructureDefinition(
        id=resource["id"],
        docstring=resource["definition"],
        type=parse_element_type(resource),
        elements={},
    )

    for element in sorted(elements, key=lambda e: len(e["path"])):
        element_id = parse_element_id(element)
        element_definition = StructureDefinition(
            id=element_id,
            docstring=element["definition"],
            type=parse_element_type(element),
            elements={},
        )

        in_focus = structure_definition
        for component in element["path"].split(".")[1:-1]:
            in_focus = in_focus.elements[component]
        in_focus.elements[element_id] = element_definition

    return structure_definition


def read_structure_definitions(
    bundle: DefinitionsBundle,
) -> Iterable[StructureDefinition]:
    raw_definitions = select_structure_definition_resources(bundle)

    return (read_structure_definition(definition) for definition in raw_definitions)


def load_from_bundle(path: str) -> Iterable[StructureDefinition]:
    with open(os.path.abspath(path), encoding="utf8") as schema_file:
        return read_structure_definitions(json.load(schema_file))
