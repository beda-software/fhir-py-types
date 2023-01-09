import argparse
import ast
import itertools
import logging
import os

from fhir_py_types.ast import build_ast
from fhir_py_types.reader.bundle import load_from_bundle


logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


def main() -> None:
    argparser = argparse.ArgumentParser(
        description="Generate Python types from FHIR resources definition"
    )
    argparser.add_argument(
        "--from-bundles",
        action="append",
        required=True,
        help="File path to read 'StructureDefinition' resources from (repeat to read multiple files)",
    )
    argparser.add_argument(
        "--outfile", required=True, help="File path to write generated Python types to"
    )
    args = argparser.parse_args()

    ast_ = itertools.chain.from_iterable(
        build_ast(load_from_bundle(bundle)) for bundle in args.from_bundles
    )

    with open(os.path.abspath(args.outfile), "w") as resource_file:
        resource_file.writelines(
            [
                "from typing import TypedDict, List as List_\n",
                "from typing_extensions import Required as Required_\n",
                "\n\n",
                "\n\n\n".join(ast.unparse(tree) for tree in ast_),
            ]
        )
