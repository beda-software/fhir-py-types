import ast

import pytest

from typing import Sequence

from fhir_py_types import (
    StructureDefinition,
    StructureDefinitionKind,
    StructurePropertyType,
)
from fhir_py_types.ast import build_ast


def compare_eq(
    definitions: Sequence[StructureDefinition], ast_tree: Sequence[ast.stmt]
):
    generated = [ast.dump(t) for t in build_ast(definitions)]
    expected = [ast.dump(t) for t in ast_tree]

    return generated == expected


def test_generates_empty_ast_from_empty_definitions():
    assert build_ast([]) == []


def test_generates_class_for_flat_definition():
    assert compare_eq(
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
                                required=True,
                                isarray=False,
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
                            value=ast.Name(id="Required_"), slice=ast.Name(id="str")
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
    assert compare_eq(
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
                                code="str",
                                required=True,
                                isarray=False,
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
                                    slice=ast.Name(id="str"),
                                )
                            ],
                        ),
                    ],
                    keywords=[ast.keyword(arg="total", value=ast.Name("False"))],
                ),
            ),
        ],
    )


def test_generates_alias_for_primitive_kind_definition():
    assert compare_eq(
        [
            StructureDefinition(
                id="TestResource",
                docstring="test resource description",
                type=[StructurePropertyType(code="str", required=True, isarray=False)],
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
    )


def test_generates_multiple_classes_for_compound_definition():
    assert compare_eq(
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
                                code="NestedTestResource",
                                required=True,
                                isarray=False,
                            )
                        ],
                        elements={
                            "property1": StructureDefinition(
                                id="property1",
                                docstring="nested test resource property 1",
                                type=[
                                    StructurePropertyType(
                                        code="str",
                                        required=True,
                                        isarray=False,
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
                            value=ast.Name(id="Required_"), slice=ast.Name(id="str")
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
                            slice=ast.Name(id="NestedTestResource"),
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
            ast.Name(id="str"),
        ),
        (
            True,
            False,
            ast.Subscript(value=ast.Name(id="Required_"), slice=ast.Name(id="str")),
        ),
        (
            False,
            True,
            ast.Subscript(value=ast.Name(id="List_"), slice=ast.Name(id="str")),
        ),
        (
            True,
            True,
            ast.Subscript(
                value=ast.Name(id="Required_"),
                slice=ast.Subscript(
                    value=ast.Name(id="List_"), slice=ast.Name(id="str")
                ),
            ),
        ),
    ],
)
def test_generates_annotations_according_to_structure_type(
    required, isarray, expected_annotation
):
    assert compare_eq(
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
