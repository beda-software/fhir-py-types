import ast
import itertools
import keyword
import logging

from dataclasses import replace
from enum import Enum, auto
from typing import Iterable, List, Literal, Tuple

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)


logger = logging.getLogger(__name__)


class AnnotationForm(Enum):
    Property = auto()
    TypeAlias = auto()
    Dict = auto()


def make_type_annotation(
    type_: StructurePropertyType, form: AnnotationForm
) -> ast.expr:
    annotation: ast.expr = ast.Name(type_.code)

    if type_.isarray:
        annotation = ast.Subscript(value=ast.Name("List_"), slice=annotation)

    if type_.required and form != AnnotationForm.TypeAlias:
        annotation = ast.Subscript(value=ast.Name("Required_"), slice=annotation)

    return annotation


def format_identifier(
    definition: StructureDefinition, type_: StructurePropertyType
) -> str:
    polymorphic = len(definition.type or []) > 1

    return definition.id + type_.code.capitalize() if polymorphic else definition.id


def zip_identifier_annotation(
    definition: StructureDefinition, form: AnnotationForm
) -> Iterable[Tuple[str, ast.expr]]:
    return (
        [
            (format_identifier(definition, t), make_type_annotation(t, form))
            for t in definition.type
        ]
        if definition.type
        else [(definition.id, ast.Name("Any_"))]
    )


def make_assignment_statement(
    identifier: str,
    annotation: ast.expr,
    form: Literal[AnnotationForm.Property, AnnotationForm.TypeAlias],
) -> ast.stmt:
    match form:
        case AnnotationForm.Property:
            return ast.AnnAssign(
                target=ast.Name(identifier), annotation=annotation, simple=1
            )
        case AnnotationForm.TypeAlias:
            return ast.Assign(targets=[ast.Name(identifier)], value=annotation)


def type_annotate(
    defintion: StructureDefinition,
    form: Literal[AnnotationForm.Property, AnnotationForm.TypeAlias],
) -> Iterable[ast.stmt]:
    return itertools.chain.from_iterable(
        [
            make_assignment_statement(identifier, annotation, form),
            ast.Expr(value=ast.Str(defintion.docstring)),
        ]
        for (identifier, annotation) in zip_identifier_annotation(defintion, form)
    )


def define_class(definition: StructureDefinition) -> Iterable[ast.stmt]:
    return [
        ast.ClassDef(
            definition.id,
            bases=[ast.Name("TypedDict")],
            body=[
                ast.Expr(value=ast.Str(definition.docstring)),
                *itertools.chain.from_iterable(
                    type_annotate(property, AnnotationForm.Property)
                    for property in definition.elements.values()
                ),
            ],
            decorator_list=[],
            keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
        )
    ]


def define_class_functional(definition: StructureDefinition) -> Iterable[ast.stmt]:
    """
    Build TypedDict for StructureDefinition with keyword properties,
    does not include docstrings
    """
    properties = list(
        itertools.chain.from_iterable(
            zip_identifier_annotation(property, AnnotationForm.Dict)
            for property in definition.elements.values()
        )
    )

    return [
        ast.Assign(
            targets=[ast.Name(definition.id)],
            value=ast.Call(
                func=ast.Name("TypedDict"),
                args=[
                    ast.Str(definition.id),
                    ast.Dict(
                        keys=[ast.Str(identifier) for identifier, _ in properties],
                        values=[annotation for _, annotation in properties],
                    ),
                ],
                keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
            ),
        )
    ]


def define_alias(definition: StructureDefinition) -> Iterable[ast.stmt]:
    return type_annotate(
        replace(definition, type=definition.elements["value"].type),
        AnnotationForm.TypeAlias,
    )


def has_keywords(definition: StructureDefinition) -> bool:
    return any(
        keyword.iskeyword(format_identifier(property, t))
        for property in definition.elements.values()
        for t in (property.type or [])
    )


def build_ast(
    structure_definitions: Iterable[StructureDefinition],
) -> Iterable[ast.stmt]:
    typedefinitions: List[ast.stmt] = []

    for definition in structure_definitions:
        match definition.kind:
            case StructureDefinitionKind.RESOURCE | StructureDefinitionKind.COMPLEX:
                if has_keywords(definition):
                    typedefinitions.extend(define_class_functional(definition))
                else:
                    typedefinitions.extend(define_class(definition))

            case StructureDefinitionKind.PRIMITIVE:
                typedefinitions.extend(define_alias(definition))

            case _:
                logger.warning(
                    "Unsupported definition {} of kind {}, skipping".format(
                        definition.id, definition.kind
                    )
                )

    return typedefinitions
