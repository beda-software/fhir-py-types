import ast
import functools
import itertools
import keyword
import logging

from dataclasses import replace
from enum import Enum, auto
from typing import Iterable, List, Literal, Tuple, cast

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
    is_polymorphic,
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
    definition: StructureDefinition, identifier: str, type_: StructurePropertyType
) -> str:
    uppercamelcase = lambda s: s[:1].upper() + s[1:]

    return (
        identifier + uppercamelcase(type_.code)
        if is_polymorphic(definition)
        else identifier
    )


def zip_identifier_annotation(
    definition: StructureDefinition, identifier: str, form: AnnotationForm
) -> Iterable[Tuple[str, ast.expr]]:
    return (
        (format_identifier(definition, identifier, t), make_type_annotation(t, form))
        for t in definition.type
    )


def make_assignment_statement(
    target: str,
    annotation: ast.expr,
    form: Literal[AnnotationForm.Property, AnnotationForm.TypeAlias],
) -> ast.stmt:
    match form:
        case AnnotationForm.Property:
            return ast.AnnAssign(
                target=ast.Name(target), annotation=annotation, simple=1
            )
        case AnnotationForm.TypeAlias:
            return ast.Assign(targets=[ast.Name(target)], value=annotation)


def type_annotate(
    defintion: StructureDefinition,
    identifier: str,
    form: Literal[AnnotationForm.Property, AnnotationForm.TypeAlias],
) -> Iterable[ast.stmt]:
    return itertools.chain.from_iterable(
        [
            make_assignment_statement(identifier_, annotation, form),
            ast.Expr(value=ast.Str(defintion.docstring)),
        ]
        for (identifier_, annotation) in zip_identifier_annotation(
            defintion, identifier, form
        )
    )


def define_class_object(
    definition: StructureDefinition, base="TypedDict"
) -> Iterable[ast.stmt]:
    return [
        ast.ClassDef(
            definition.id,
            bases=[ast.Name(base)],
            body=[
                ast.Expr(value=ast.Str(definition.docstring)),
                *itertools.chain.from_iterable(
                    type_annotate(property, identifier, AnnotationForm.Property)
                    for identifier, property in definition.elements.items()
                ),
            ],
            decorator_list=[],
            keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
        )
    ]


def define_class_functional(
    definition: StructureDefinition, base="TypedDict"
) -> Iterable[ast.stmt]:
    """
    Build TypedDict for StructureDefinition with keyword properties,
    does not include docstrings
    """
    properties = list(
        itertools.chain.from_iterable(
            zip_identifier_annotation(property, identifier, AnnotationForm.Dict)
            for identifier, property in definition.elements.items()
        )
    )

    return [
        ast.Assign(
            targets=[ast.Name(definition.id)],
            value=ast.Call(
                func=ast.Name(base),
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


def define_class(
    definition: StructureDefinition, base="TypedDict"
) -> Iterable[ast.stmt]:
    if has_keywords(definition):
        return define_class_functional(definition, base=base)
    else:
        return define_class_object(definition, base=base)


def define_alias(definition: StructureDefinition) -> Iterable[ast.stmt]:
    return type_annotate(definition, definition.id, AnnotationForm.TypeAlias)


def define_polymorphic(definition: StructureDefinition) -> Iterable[ast.stmt]:
    base = replace(
        definition,
        id="_" + definition.id + "Base",
        elements={
            k: p for k, p in definition.elements.items() if not is_polymorphic(p)
        },
    )

    polymorphics = next(
        [
            StructureDefinition(
                id="_" + format_identifier(p, definition.id, t),
                docstring=p.docstring,
                type=[
                    StructurePropertyType(code=format_identifier(p, definition.id, t))
                ],
                elements={format_identifier(p, k, t): replace(p, type=[t])},
                kind=StructureDefinitionKind.COMPLEX,
            )
            for t in p.type
        ]
        for k, p in definition.elements.items()
        if is_polymorphic(p)
    )

    return itertools.chain.from_iterable(
        [
            define_class(base),
            itertools.chain.from_iterable(
                define_class(p, base=base.id) for p in polymorphics
            ),
            [
                ast.Assign(
                    targets=[ast.Name(definition.id)],
                    value=functools.reduce(
                        lambda acc, n: ast.BinOp(left=acc, right=n, op=ast.BitOr()),
                        [cast(ast.expr, ast.Name(d.id)) for d in polymorphics],
                    ),
                )
            ],
        ],
    )


def has_keywords(definition: StructureDefinition) -> bool:
    return any(
        keyword.iskeyword(format_identifier(property, identifier, t))
        for identifier, property in definition.elements.items()
        for t in property.type
    )


def has_required_polymorphics(definition: StructureDefinition) -> bool:
    return any(
        is_polymorphic(e) and any(t.required for t in e.type)
        for e in definition.elements.values()
    )


def select_nested_definitions(
    definition: StructureDefinition,
) -> Iterable[StructureDefinition]:
    return (
        d
        for d in definition.elements.values()
        if d.kind == StructureDefinitionKind.COMPLEX
    )


def iterate_definitions_tree(
    root: StructureDefinition,
) -> Iterable[StructureDefinition]:
    subtree = list(select_nested_definitions(root))

    while subtree:
        tree_node = subtree.pop()
        yield tree_node
        subtree.extend(select_nested_definitions(tree_node))

    yield root


def build_ast(
    structure_definitions: Iterable[StructureDefinition],
) -> Iterable[ast.stmt]:
    typedefinitions: List[ast.stmt] = []

    for root in structure_definitions:
        for definition in iterate_definitions_tree(root):
            match definition.kind:
                case StructureDefinitionKind.RESOURCE | StructureDefinitionKind.COMPLEX:
                    if has_required_polymorphics(definition):
                        typedefinitions.extend(define_polymorphic(definition))
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
