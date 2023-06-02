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

    if not type_.required and form != AnnotationForm.TypeAlias and not type_.isarray:
        annotation = ast.Subscript(value=ast.Name("Optional_"), slice=annotation)

    return annotation


def make_default_initializer(identifier: str, type_: StructurePropertyType):
    default_value = ast.Constant(None)
    keywords: List[ast.keyword] = []
    if type_.isarray and not type_.required:
        keywords.append(ast.keyword(arg="default_factory", value=ast.Name("list")))
    else:
        if type_.required:
            default_value = ast.Ellipsis()
        elif type_.literal:
            default_value = ast.Str(type_.code)
        else:
            default_value = ast.Constant(None)
        keywords.append(ast.keyword(arg="default", value=default_value))
    if keyword.iskeyword(identifier):
        keywords.append(
            ast.keyword(arg="alias", value=ast.Constant(identifier)),
        )
    default = ast.Call(
            ast.Name("Field"),
            args=[],
            keywords=keywords,
        )

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


def remap_type(definition: StructureDefinition, type_: StructurePropertyType):
    if not type_.literal:
        match type_.code:
            case "Resource":
                # Different contexts use 'Resource' type to refer to any
                # resource differentiated by its 'resourceType' (tagged union).
                # 'AnyResource' is not defined by the spec but rather
                # generated as a union of all defined resource types.
                type_ = replace(type_, code="AnyResource")

    if is_polymorphic(definition):
        # Required polymorphic types are not yet supported.
        # Making multiple polymorphic properties required means
        # no valid resource model can be generated (due to required conflicts).
        # Future implementation might include optional properties
        # with a custom validator that will enforce single required property rule.
        type_ = replace(type_, required=False)

    return type_


def zip_identifier_type(
    definition: StructureDefinition, identifier: str
) -> Iterable[Tuple[str, StructurePropertyType]]:
    return (
        (format_identifier(definition, identifier, t), t)
        for t in [remap_type(definition, t) for t in definition.type]
    )


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
) -> Iterable[ast.stmt | ast.expr]:
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
        ),
        ast.Call(
            ast.Attribute(value=ast.Name(definition.id), attr="update_forward_refs"),
            args=[],
            keywords=[],
        ),
    ]


def define_class(
    definition: StructureDefinition, base="BaseModel"
) -> Iterable[ast.stmt | ast.expr]:
    return define_class_object(definition, base=base)


def define_alias(definition: StructureDefinition) -> Iterable[ast.stmt]:
    return type_annotate(definition, definition.id, AnnotationForm.TypeAlias)


def define_tagged_union(
    name: str, components: Iterable[StructureDefinition], distinct_by: str
) -> ast.stmt:
    annotation = functools.reduce(
        lambda acc, n: ast.BinOp(left=acc, right=n, op=ast.BitOr()),
        (cast(ast.expr, ast.Name(d.id)) for d in components),
    )

    return ast.Assign(
        targets=[ast.Name(name)],
        value=ast.Subscript(
            value=ast.Name("Annotated_"),
            slice=ast.Tuple(
                elts=[
                    annotation,
                    ast.Call(
                        ast.Name("Field"),
                        args=[ast.Constant(...)],
                        keywords=[
                            ast.keyword(
                                arg="discriminator", value=ast.Constant(distinct_by)
                            ),
                        ],
                    ),
                ]
            ),
        ),
    )


def select_tagged_resources(
    definitions: Iterable[StructureDefinition], key: str
) -> Iterable[StructureDefinition]:
    return (
        definition
        for definition in definitions
        if definition.kind == StructureDefinitionKind.RESOURCE
        and key in definition.elements
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
) -> Iterable[ast.stmt | ast.expr]:
    structure_definitions = list(structure_definitions)
    typedefinitions: List[ast.stmt | ast.expr] = []

    for root in structure_definitions:
        for definition in iterate_definitions_tree(root):
            match definition.kind:
                case StructureDefinitionKind.RESOURCE | StructureDefinitionKind.COMPLEX:
                    typedefinitions.extend(define_class(definition))

                case StructureDefinitionKind.PRIMITIVE:
                    typedefinitions.extend(define_alias(definition))

                case _:
                    logger.warning(
                        "Unsupported definition {} of kind {}, skipping".format(
                            definition.id, definition.kind
                        )
                    )

    resources = list(select_tagged_resources(structure_definitions, key="resourceType"))
    if resources:
        typedefinitions.append(
            define_tagged_union(
                name="AnyResource", components=resources, distinct_by="resourceType"
            )
        )

    return sorted(
        typedefinitions,
        # Defer any postprocessing until after the structure tree is defined.
        key=lambda definition: 1 if isinstance(definition, ast.Call) else 0,
    )
