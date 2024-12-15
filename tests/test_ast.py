import ast
from collections.abc import Sequence

import pytest

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)
from fhir_py_types.ast import build_ast


def assert_eq(
    definitions: Sequence[StructureDefinition], ast_tree: Sequence[ast.stmt | ast.expr]
) -> None:
    generated = [ast.dump(t) for t in build_ast(definitions)]
    expected = [ast.dump(t) for t in ast_tree]

    assert generated == expected


def build_field_with_alias(identifier: str) -> ast.Call:
    return ast.Call(
        func=ast.Name(id="Field"),
        args=[],
        keywords=[
            ast.keyword(arg="default", value=ast.Constant(value=None)),
            ast.keyword(arg="alias", value=ast.Constant(value=identifier)),
        ],
    )


def test_generates_empty_ast_from_empty_definitions() -> None:
    assert build_ast([]) == []


def test_generates_class_for_flat_definition() -> None:
    assert_eq(
        [
            StructureDefinition(
                id="TestResource",
                docstring="test resource description",
                type=[
                    StructurePropertyType(
                        code="TestResource", required=True, isarray=False
                    )
                ],
                elements={
                    "property1": StructureDefinition(
                        id="property1",
                        docstring="test resource property 1",
                        type=[
                            StructurePropertyType(
                                code="str", required=True, isarray=False
                            )
                        ],
                        elements={},
                    )
                },
                kind=StructureDefinitionKind.RESOURCE,
            )
        ],
        [
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id='AnyResource'), ast.Name(id="BaseModel")],
                keywords=[],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Constant("str"),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1__ext"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Element"),
                        ),
                        value=build_field_with_alias("_property1"),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
                type_params=[],
            ),
        ],
    )


@pytest.mark.parametrize(
    ("definitions", "ast_tree"),
    [
        (
            [
                StructureDefinition(
                    id="date",
                    docstring="date description",
                    type=[
                        StructurePropertyType(code="str", required=True, isarray=False)
                    ],
                    elements={},
                    kind=StructureDefinitionKind.PRIMITIVE,
                )
            ],
            [
                ast.Assign(
                    targets=[ast.Name("dateType")],
                    value=ast.Name("str"),
                ),
                ast.Expr(value=ast.Constant("date description")),
            ],
        ),
    ],
)
def test_generates_alias_for_primitive_kind_definition(
    definitions: list[StructureDefinition], ast_tree: list[ast.stmt]
) -> None:
    assert_eq(definitions, ast_tree)


def test_generates_multiple_classes_for_compound_definition() -> None:
    assert_eq(
        [
            StructureDefinition(
                id="TestResource",
                docstring="test resource description",
                type=[
                    StructurePropertyType(
                        code="TestResource", required=True, isarray=False
                    )
                ],
                elements={
                    "complexproperty": StructureDefinition(
                        id="NestedComplex",
                        docstring="nested complex definition",
                        type=[
                            StructurePropertyType(
                                code="NestedTestResource", required=True, isarray=False
                            )
                        ],
                        elements={
                            "property1": StructureDefinition(
                                id="property1",
                                docstring="nested test resource property 1",
                                type=[
                                    StructurePropertyType(
                                        code="str", required=False, isarray=False
                                    )
                                ],
                                elements={},
                            )
                        },
                        kind=StructureDefinitionKind.COMPLEX,
                    )
                },
                kind=StructureDefinitionKind.RESOURCE,
            )
        ],
        [
            ast.ClassDef(
                name="NestedComplex",
                bases=[ast.Name(id="BaseModel")],
                keywords=[],
                body=[
                    ast.Expr(value=ast.Constant(value="nested complex definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"), slice=ast.Constant("str")
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="nested test resource property 1")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="property1__ext"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Element"),
                        ),
                        simple=1,
                        value=build_field_with_alias("_property1"),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="nested test resource property 1")
                    ),
                ],
                decorator_list=[],
                type_params=[],
            ),
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id="AnyResource"), ast.Name(id="BaseModel")],
                keywords=[],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="complexproperty"),
                        annotation=ast.Constant("NestedTestResource"),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="nested complex definition")),
                ],
                decorator_list=[],
                type_params=[],
            ),
        ],
    )


@pytest.mark.parametrize(
    ("required", "isarray", "literal", "expected_annotation"),
    [
        (
            False,
            False,
            False,
            ast.Subscript(value=ast.Name(id="Optional_"), slice=ast.Constant("str")),
        ),
        (
            True,
            False,
            False,
            ast.Constant("str"),
        ),
        (
            False,
            True,
            False,
            ast.Subscript(
                value=ast.Name(id="Optional_"),
                slice=ast.Subscript(
                    value=ast.Name(id="List_"), slice=ast.Constant("str")
                ),
            ),
        ),
        (
            True,
            True,
            False,
            ast.Subscript(value=ast.Name(id="List_"), slice=ast.Constant("str")),
        ),
        (
            True,
            False,
            True,
            ast.Subscript(value=ast.Name(id="Literal_"), slice=ast.Constant("str")),
        ),
        (
            False,
            False,
            True,
            ast.Subscript(
                value=ast.Name(id="Optional_"),
                slice=ast.Subscript(
                    value=ast.Name(id="Literal_"), slice=ast.Constant("str")
                ),
            ),
        ),
    ],
)
def test_generates_annotations_according_to_structure_type(
    required: bool,
    isarray: bool,
    literal: bool,
    expected_annotation: ast.Subscript | ast.Constant,
) -> None:
    assert_eq(
        [
            StructureDefinition(
                id="TestResource",
                docstring="test resource description",
                type=[
                    StructurePropertyType(
                        code="TestResource", required=True, isarray=False
                    )
                ],
                elements={
                    "property1": StructureDefinition(
                        id="property1",
                        docstring="test resource property 1",
                        type=[
                            StructurePropertyType(
                                code="str",
                                required=required,
                                isarray=isarray,
                                literal=literal,
                            )
                        ],
                        elements={},
                    )
                },
                kind=StructureDefinitionKind.RESOURCE,
            )
        ],
        [
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id='AnyResource'), ast.Name(id="BaseModel")],
                keywords=[],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=expected_annotation,
                        simple=1,
                        value=ast.Constant(None)
                        if not required
                        else ast.Constant("str")
                        if literal
                        else None,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1__ext"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Subscript(
                                value=ast.Name(id="List_"),
                                slice=ast.Constant("Element"),
                            ),
                        )
                        if isarray
                        else ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Element"),
                        ),
                        simple=1,
                        value=build_field_with_alias("_property1"),
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
                type_params=[],
            ),
        ],
    )


def test_unrolls_required_polymorphic_into_class_union() -> None:
    assert_eq(
        [
            StructureDefinition(
                id="TestResource",
                docstring="test resource description",
                type=[
                    StructurePropertyType(
                        code="TestResource", required=True, isarray=False
                    )
                ],
                elements={
                    "monotype": StructureDefinition(
                        id="monotype",
                        docstring="monotype property definition",
                        type=[
                            StructurePropertyType(
                                code="boolean", required=False, isarray=False
                            ),
                        ],
                        elements={},
                    ),
                    "value": StructureDefinition(
                        id="value",
                        docstring="polymorphic property definition",
                        type=[
                            StructurePropertyType(
                                code="boolean", required=True, isarray=False
                            ),
                            StructurePropertyType(
                                code="Quantity", required=True, isarray=False
                            ),
                        ],
                        elements={},
                    ),
                },
                kind=StructureDefinitionKind.RESOURCE,
            )
        ],
        [
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id='AnyResource'),ast.Name(id="BaseModel")],
                keywords=[],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="monotype"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("booleanType"),
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(value=ast.Constant(value="monotype property definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="monotype__ext"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Element"),
                        ),
                        simple=1,
                        value=build_field_with_alias("_monotype"),
                    ),
                    ast.Expr(value=ast.Constant(value="monotype property definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="valueBoolean"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("booleanType"),
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="valueBoolean__ext"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Element"),
                        ),
                        simple=1,
                        value=build_field_with_alias("_valueBoolean"),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="valueQuantity"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"),
                            slice=ast.Constant("Quantity"),
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                ],
                decorator_list=[],
                type_params=[],
            ),
        ],
    )
