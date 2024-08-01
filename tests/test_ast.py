import ast
from collections.abc import Sequence

import pytest

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)
from fhir_py_types.ast import build_ast

EXPECTED_BASE_MODEL_CONFIG = [
    ast.keyword(
        arg="extra",
        value=ast.Attribute(value=ast.Name("Extra"), attr="forbid"),
    ),
    ast.keyword(arg="validate_assignment", value=ast.Constant(True)),
]


def assert_eq(
    definitions: Sequence[StructureDefinition], ast_tree: Sequence[ast.stmt | ast.expr]
) -> None:
    generated = [ast.dump(t) for t in build_ast(definitions)]
    expected = [ast.dump(t) for t in ast_tree]

    assert generated == expected


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
                bases=[ast.Name(id="BaseModel")],
                keywords=EXPECTED_BASE_MODEL_CONFIG,
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Str("str"),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
            ),
            ast.Call(
                ast.Attribute(value=ast.Name("TestResource"), attr="model_rebuild"),
                args=[],
                keywords=[],
            ),
        ],
    )


@pytest.mark.parametrize(
    ("definitions", "ast_tree"),
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
                name="NestedTestResource",
                bases=[ast.Name(id="BaseModel")],
                keywords=EXPECTED_BASE_MODEL_CONFIG,
                body=[
                    ast.Expr(value=ast.Constant(value="nested resource definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"), slice=ast.Str("str")
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="nested test resource property 1")
                    ),
                ],
                decorator_list=[],
            ),
            ast.ClassDef(
                name="TestResource",
                bases=[ast.Name(id="BaseModel")],
                keywords=EXPECTED_BASE_MODEL_CONFIG,
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="complexproperty"),
                        annotation=ast.Str("NestedTestResource"),
                        simple=1,
                    ),
                    ast.Expr(value=ast.Constant(value="nested resource definition")),
                ],
                decorator_list=[],
            ),
            ast.Call(
                ast.Attribute(
                    value=ast.Name("NestedTestResource"), attr="model_rebuild"
                ),
                args=[],
                keywords=[],
            ),
            ast.Call(
                ast.Attribute(value=ast.Name("TestResource"), attr="model_rebuild"),
                args=[],
                keywords=[],
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
            ast.Subscript(value=ast.Name(id="Optional_"), slice=ast.Str("str")),
        ),
        (
            True,
            False,
            False,
            ast.Str("str"),
        ),
        (
            False,
            True,
            False,
            ast.Subscript(
                value=ast.Name(id="Optional_"),
                slice=ast.Subscript(value=ast.Name(id="List_"), slice=ast.Str("str")),
            ),
        ),
        (
            True,
            True,
            False,
            ast.Subscript(value=ast.Name(id="List_"), slice=ast.Str("str")),
        ),
        (
            True,
            False,
            True,
            ast.Subscript(value=ast.Name(id="Literal_"), slice=ast.Str("str")),
        ),
        (
            False,
            False,
            True,
            ast.Subscript(
                value=ast.Name(id="Optional_"),
                slice=ast.Subscript(
                    value=ast.Name(id="Literal_"), slice=ast.Str("str")
                ),
            ),
        ),
    ],
)
def test_generates_annotations_according_to_structure_type(
    required: bool,
    isarray: bool,
    literal: bool,
    expected_annotation: ast.Subscript | ast.Str,
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
                bases=[ast.Name(id="BaseModel")],
                keywords=EXPECTED_BASE_MODEL_CONFIG,
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="property1"),
                        annotation=expected_annotation,
                        simple=1,
                        value=ast.Constant(None)
                        if not required
                        else ast.Str("str")
                        if literal
                        else None,
                    ),
                    ast.Expr(value=ast.Constant(value="test resource property 1")),
                ],
                decorator_list=[],
            ),
            ast.Call(
                ast.Attribute(value=ast.Name("TestResource"), attr="model_rebuild"),
                args=[],
                keywords=[],
            ),
        ],
    )


def test_unrolls_required_polymorphic_into_class_uion() -> None:
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
                bases=[ast.Name(id="BaseModel")],
                keywords=EXPECTED_BASE_MODEL_CONFIG,
                body=[
                    ast.Expr(value=ast.Constant(value="test resource description")),
                    ast.AnnAssign(
                        target=ast.Name(id="monotype"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"), slice=ast.Str("boolean")
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(value=ast.Constant(value="monotype property definition")),
                    ast.AnnAssign(
                        target=ast.Name(id="valueBoolean"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"), slice=ast.Str("boolean")
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                    ast.AnnAssign(
                        target=ast.Name(id="valueQuantity"),
                        annotation=ast.Subscript(
                            value=ast.Name(id="Optional_"), slice=ast.Str("Quantity")
                        ),
                        simple=1,
                        value=ast.Constant(None),
                    ),
                    ast.Expr(
                        value=ast.Constant(value="polymorphic property definition")
                    ),
                ],
                decorator_list=[],
            ),
            ast.Call(
                ast.Attribute(value=ast.Name("TestResource"), attr="model_rebuild"),
                args=[],
                keywords=[],
            ),
        ],
    )
