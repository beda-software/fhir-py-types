import ast

import pytest

from typing import Sequence

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)
from fhir_py_types.ast import build_ast


def assert_eq(definitions: Sequence[StructureDefinition], ast_tree: Sequence[ast.stmt]):
    generated = [ast.dump(t) for t in build_ast(definitions)]
    expected = [ast.dump(t) for t in ast_tree]

    assert generated == expected


def test_generates_empty_ast_from_empty_definitions():
    assert build_ast([]) == []


def test_generates_class_for_flat_definition():
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
                bases=[ast.Name(id="TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"), slice=ast.Str("str")
                        ),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
            )
        ],
    )


def test_generates_function_call_for_keyworded_definition():
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
                    "class": StructureDefinition(
                        id="class",
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
            ast.Assign(
                targets=[ast.Name("TestResource")],
                value=ast.Call(
                    func=ast.Name("TypedDict"),
                    args=[
                        ast.Str("TestResource"),
                        ast.Dict(
                            keys=[ast.Str("class")],
                            values=[
                                ast.Subscript(
                                    value=ast.Name(id="Required_"),
                                    slice=ast.Str("str"),
                                )
                            ],
                        ),
                    ],
                    keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
                ),
            ),
        ],
    )


@pytest.mark.parametrize(
    "definitions, ast_tree",
    [
        (
            [
                StructureDefinition(
                    id="TestResource",
                    docstring="test resource description",
                    type=[
                        StructurePropertyType(code="str", required=True, isarray=False)
                    ],
                    elements={},
                    kind=StructureDefinitionKind.PRIMITIVE,
                )
            ],
            [
                ast.Assign(
                    targets=[ast.Name("TestResource")],
                    value=ast.Name("str"),
                ),
                ast.Expr(value=ast.Str("test resource description")),
            ],
        ),
    ],
)
def test_generates_alias_for_primitive_kind_definition(definitions, ast_tree):
    assert_eq(definitions, ast_tree)


def test_generates_multiple_classes_for_compound_definition():
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
                        id="NestedTestResource",
                        docstring="nested resource definition",
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
                                        code="str", required=True, isarray=False
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
                name="NestedTestResource",
                bases=[ast.Name(id="TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(value=ast.Constant(value="nested resource definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"), slice=ast.Str("str")
                        ),
                        simple=1,
                    ),
                    ast.Expr(
                        value=ast.Constant(value="nested test resource property 1")
                    ),
                ],
                decorator_list=[],
            ),
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id="TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="complexproperty"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"),
                            slice=ast.Str("NestedTestResource"),
                        ),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="nested resource definition")),
                ],
                decorator_list=[],
            ),
        ],
    )


@pytest.mark.parametrize(
    "required, isarray, expected_annotation",
    [
        (
            False,
            False,
            ast.Str("str"),
        ),
        (
            True,
            False,
            ast.Subscript(value=ast.Name(id="Required_"), slice=ast.Str("str")),
        ),
        (
            False,
            True,
            ast.Subscript(value=ast.Name(id="List_"), slice=ast.Str("str")),
        ),
        (
            True,
            True,
            ast.Subscript(
                value=ast.Name(id="Required_"),
                slice=ast.Subscript(value=ast.Name(id="List_"), slice=ast.Str("str")),
            ),
        ),
    ],
)
def test_generates_annotations_according_to_structure_type(
    required, isarray, expected_annotation
):
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
                                code="str", required=required, isarray=isarray
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
                bases=[ast.Name(id="TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=expected_annotation,
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
            )
        ],
    )


def test_unrolls_required_polymorphic_into_class_uion():
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
                                code="boolean", required=True, isarray=False
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
                name="_TestResourceBase",
                bases=[ast.Name(id="TypedDict")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="monotype"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"), slice=ast.Str("boolean")
                        ),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="monotype property definition")),
                ],
                decorator_list=[],
            ),
            ast.ClassDef(
                name="_TestResourceBoolean",
                bases=[ast.Name(id="_TestResourceBase")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="valueBoolean"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"), slice=ast.Str("boolean")
                        ),
                        simple=1,
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                ],
                decorator_list=[],
            ),
            ast.ClassDef(
                name="_TestResourceQuantity",
                bases=[ast.Name(id="_TestResourceBase")],
                keywords=[ast.keyword(arg="total", value=ast.Name(id="False"))],
                body=[
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="valueQuantity"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Required_"), slice=ast.Str("Quantity")
                        ),
                        simple=1,
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                ],
                decorator_list=[],
            ),
            ast.Assign(
                targets=[ast.Name("TestResource")],
                value=ast.BinOp(
                    left=ast.Name("_TestResourceBoolean"),
                    right=ast.Name("_TestResourceQuantity"),
                    op=ast.BitOr(),
                ),
            ),
        ],
    )
