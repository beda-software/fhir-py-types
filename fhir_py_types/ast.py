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
    match form:
        case AnnotationForm.TypeAlias:
            annotation: ast.expr = ast.Name(type_.code)
        case _:
            annotation = ast.Str(type_.code)

    if type_.literal:
        annotation = ast.Subscript(value=ast.Name("Literal_"), slice=annotation)

    if type_.isarray:
        annotation = ast.Subscript(value=ast.Name("List_"), slice=annotation)

    if not type_.required and form != AnnotationForm.TypeAlias:
        annotation = ast.Subscript(value=ast.Name("Optional_"), slice=annotation)

    return annotation


def make_default_initializer(identifier: str, type_: StructurePropertyType):
    default: ast.expr | None = None

    if keyword.iskeyword(identifier):
        default = ast.Call(
            ast.Name("Field"),
            args=[],
            keywords=[
                *(
                    [ast.keyword(arg="default", value=ast.Constant(None))]
                    if not type_.required
                    else []
                ),
                ast.keyword(arg="alias", value=ast.Constant(identifier)),
            ],
        )
    else:
        if not type_.required:
            default = ast.Constant(None)
        elif type_.literal and not type_.isarray:
            default = ast.Str(type_.code)

    return default


def format_identifier(
    definition: StructureDefinition, identifier: str, type_: StructurePropertyType
) -> str:
    uppercamelcase = lambda s: s[:1].upper() + s[1:]

    return (
        identifier + uppercamelcase(type_.code)
        if is_polymorphic(definition)
        else identifier
    )


def zip_identifier_type(
    definition: StructureDefinition, identifier: str
) -> Iterable[Tuple[str, StructurePropertyType]]:
    return ((format_identifier(definition, identifier, t), t) for t in definition.type)


def make_assignment_statement(
    target: str,
    annotation: ast.expr,
    form: Literal[AnnotationForm.Property, AnnotationForm.TypeAlias],
    default: ast.expr | None = None,
) -> ast.stmt:
    match form:
        case AnnotationForm.Property:
            return ast.AnnAssign(
                target=ast.Name(target), annotation=annotation, simple=1, value=default
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
            make_assignment_statement(
                identifier_ + "_" if keyword.iskeyword(identifier_) else identifier_,
                make_type_annotation(type_, form),
                form,
                default=make_default_initializer(identifier_, type_),
            ),
            ast.Expr(value=ast.Str(defintion.docstring)),
        ]
        for (identifier_, type_) in zip_identifier_type(defintion, identifier)
    )


def order_type_overriding_properties(
    properties_definition: dict[str, StructureDefinition]
) -> Iterable[Tuple[str, StructureDefinition]]:
    property_types = {
        t.code for definition in properties_definition.values() for t in definition.type
    }
    return sorted(
        properties_definition.items(),
        key=lambda definition: 1 if definition[0] in property_types else -1,
    )


def define_class_object(
    definition: StructureDefinition, base="BaseModel"
) -> Iterable[ast.stmt]:
    match base:
        case "BaseModel":
            base_class_kwargs: Iterable[ast.keyword] = [
                ast.keyword(
                    arg="extra",
                    value=ast.Attribute(value=ast.Name("Extra"), attr="forbid"),
                ),
                ast.keyword(arg="validate_assignment", value=ast.Constant(True)),
            ]
        case _:
            base_class_kwargs = []

    return [
        ast.ClassDef(
            definition.id,
            bases=[ast.Name(base)],
            body=[
                ast.Expr(value=ast.Str(definition.docstring)),
                *itertools.chain.from_iterable(
                    type_annotate(property, identifier, AnnotationForm.Property)
                    for identifier, property in order_type_overriding_properties(
                        definition.elements
                    )
                ),
            ],
            decorator_list=[],
            keywords=base_class_kwargs,
        )
    ]


def define_class(
    definition: StructureDefinition, base="BaseModel"
) -> Iterable[ast.stmt]:
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
