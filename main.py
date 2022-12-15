import ast
from typing import TypedDict

import astor
import edn_format
from edn_format import Keyword, Symbol


def as_python_name(s):
    return s.name.replace("-", "_").replace("/", ".")


def list_as_or(lst):
    if len(lst) == 1:
        return ast.Name(as_python_name(lst[0]))
    else:
        right = lst.pop()
        return ast.BinOp(
            left=list_as_or(lst), right=ast.Name(as_python_name(right)), op=ast.BitOr()
        )


def get_confirms(scm):
    confirms = scm[Keyword("confirms")]
    return list_as_or(list(confirms))


def build_map(ctx, schema):
    c = ast.ClassDef("Patient")
    c.bases = [ast.Name("TypedDict")]
    c.decorator_list = []
    c.body = []

    for key, definition_schema in schema[Keyword("keys")].items():
        annotation = ast.Name(f"{key.name}")

        if definition_schema.get(Keyword("fhir/polymorphic")):
            annotation = ast.Name(f"Patient{key.name.capitalize()}")
        elif definition_schema.get(Keyword("type")) == Symbol("zen/vector"):
            annotation = ast.List(
                elts=[get_confirms(definition_schema[Keyword("every")])]
            )
        else:
            annotation = get_confirms(definition_schema)

        c.body.append(
            ast.AnnAssign(
                target=ast.Name(key.name),
                annotation=annotation,
                simple=1,
            )
        )
    return c


def build_schema(ctx, schema):
    build_fn = build_fn_map.get(schema[Keyword("type")])
    if build_fn:
        return build_fn(ctx, schema)
    else:
        print(f"Don't know how to build {schema[Keyword('type')]}")


def main():
    ctx = {}
    with open("./patient.edn") as f:
        data = edn_format.loads(f.read())
        resource_name = data[Symbol("ns")].name.split(".")[1]
        ast_def = build_schema(ctx, data[Symbol("schema")])
        print(astor.to_source(ast_def))
        # print(ast.dump(ast_def))


build_fn_map = {Symbol("zen/map"): build_map}


if __name__ == "__main__":
    main()
    # print(ast.dump(ast.parse("a: str|number")))
