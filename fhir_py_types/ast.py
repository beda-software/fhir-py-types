import ast
import functools
import itertools

from typing import Iterable, List, Tuple, cast

from fhir_py_types import StructureDefinition, StructurePropertyType


def fold_into_union_node(nodes: Iterable[ast.expr]) -> ast.expr:
    return functools.reduce(
        lambda acc, n: ast.BinOp(left=acc, right=n, op=ast.BitOr()),
        nodes,
    )


def make_type_annotation(type_: StructurePropertyType) -> ast.expr:
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

    if type_.required:
        annotation = ast.Subscript(value=ast.Name("Required_"), slice=annotation)

    return annotation


def make_ast_node(property: StructureDefinition) -> Iterable[ast.stmt]:
    choice_of_data_types: List[Tuple[StructurePropertyType | None, ast.expr]] = (
        [(t, make_type_annotation(t)) for t in property.type]
        if property.type
        else [(None, ast.Name("Any"))]
    )

    return itertools.chain.from_iterable(
        [
            ast.AnnAssign(
                target=ast.Name(
                    property.id
                    if len(choice_of_data_types) == 1 or type_ is None
                    else property.id + type_.code.capitalize()
                ),
                annotation=annotation,
                simple=1,
            ),
            ast.Expr(value=ast.Str(property.docstring)),
        ]
        for (type_, annotation) in choice_of_data_types
    )


def build_ast(
    structure_definitions: Iterable[StructureDefinition],
) -> Iterable[ast.ClassDef]:
    typedefinitions = []

    for definition in structure_definitions:
        klass = ast.ClassDef(
            definition.id,
            bases=[ast.Name("TypedDict")],
            body=[ast.Expr(value=ast.Str(definition.docstring))],
            decorator_list=[],
            keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
        )

        for property in definition.elements.values():
            klass.body.extend(make_ast_node(property))

        typedefinitions.append(klass)

    return typedefinitions
