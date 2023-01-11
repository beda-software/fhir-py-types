import ast
from dataclasses import replace
from enum import Enum, auto
import functools
import itertools
import logging

from typing import Iterable, List, Tuple, cast

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)


logger = logging.getLogger(__name__)


class AnnotationForm(Enum):
    Property = auto()
    TypeAlias = auto()


def fold_into_union_node(nodes: Iterable[ast.expr]) -> ast.expr:
    return functools.reduce(
        lambda acc, n: ast.BinOp(left=acc, right=n, op=ast.BitOr()),
        nodes,
    )


def make_type_annotation(
    type_: StructurePropertyType, form: AnnotationForm
) -> ast.expr:
    if type_.target_profile:
        annotation: ast.expr = ast.Subscript(
            value=ast.Name(type_.code),
            slice=fold_into_union_node(
                cast(ast.expr, ast.Name(n)) for n in type_.target_profile
            ),
        )
    else:
        annotation = ast.Name(type_.code)

    if type_.isarray:
        annotation = ast.Subscript(value=ast.Name("List_"), slice=annotation)

    if type_.required and form == AnnotationForm.Property:
        annotation = ast.Subscript(value=ast.Name("Required_"), slice=annotation)

    return annotation


def make_property_identifier(
    property: StructureDefinition, type_: StructurePropertyType
) -> str:
    polymorphic = len(property.type or []) > 1

    return property.id + type_.code.capitalize() if polymorphic else property.id


def make_assignment_node(
    identifier: str, annotation: ast.expr, form: AnnotationForm
) -> ast.stmt:
    match form:
        case AnnotationForm.Property:
            return ast.AnnAssign(
                target=ast.Name(identifier), annotation=annotation, simple=1
            )
        case AnnotationForm.TypeAlias:
            return ast.Assign(targets=[ast.Name(identifier)], value=annotation)


def make_annotated_node(
    property: StructureDefinition, form: AnnotationForm
) -> Iterable[ast.stmt]:
    annotated_identifiers: List[Tuple[str, ast.expr]] = (
        [
            (
                make_property_identifier(property, t),
                make_type_annotation(t, form),
            )
            for t in property.type
        ]
        if property.type
        else [(property.id, ast.Name("Any"))]
    )

    return itertools.chain.from_iterable(
        [
            make_assignment_node(identifier, annotation, form),
            ast.Expr(value=ast.Str(property.docstring)),
        ]
        for (identifier, annotation) in annotated_identifiers
    )


def build_ast(
    structure_definitions: Iterable[StructureDefinition],
) -> Iterable[ast.stmt]:
    typedefinitions: List[ast.stmt] = []

    for definition in structure_definitions:
        match definition.kind:
            case StructureDefinitionKind.RESOURCE | StructureDefinitionKind.COMPLEX:
                klass = ast.ClassDef(
                    definition.id,
                    bases=[ast.Name("TypedDict")],
                    body=[ast.Expr(value=ast.Str(definition.docstring))],
                    decorator_list=[],
                    keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
                )

                for property in definition.elements.values():
                    klass.body.extend(
                        make_annotated_node(property, AnnotationForm.Property)
                    )

                typedefinitions.append(klass)

            case StructureDefinitionKind.PRIMITIVE:
                typedefinitions.extend(
                    make_annotated_node(
                        replace(definition, type=definition.elements["value"].type),
                        AnnotationForm.TypeAlias,
                    )
                )

            case _:
                logger.warning(
                    "Unsupported definition {} of kind {}, skipping".format(
                        definition.id, definition.kind
                    )
                )

    return typedefinitions
