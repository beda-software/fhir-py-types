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
        description="Generate Python typed data models from FHIR resources definition"
    )
    argparser.add_argument(
        "--from-bundles",
        action="append",
        required=True,
        help="File path to read 'StructureDefinition' resources from (repeat to read multiple files)",
    )
    argparser.add_argument(
        "--outfile",
        required=True,
        help="File path to write generated Python typed data models to",
    )
    argparser.add_argument(
        "--base-model",
        default="pydantic.BaseModel",
        required=True,
        help="Python path to the Base Model class to use as the base class for generated models",
    )
    
    args = argparser.parse_args()

    ast_ = itertools.chain.from_iterable(
        build_ast(load_from_bundle(bundle)) for bundle in args.from_bundles
    )

    with open(os.path.abspath(args.outfile), "w") as resource_file:
        resource_file.writelines(
            [
                "from typing import List as List_, Optional as Optional_, Literal as Literal_, Annotated as Annotated_\n",
                "from datetime import time, date, datetime\n",
                "from %s import %s as BaseModel\n" % tuple(args.base_model.rsplit(".", 1))
                "from pydantic import Field, Extra\n",
                "\n\n",
                "\n\n\n".join(
                    ast.unparse(ast.fix_missing_locations(tree)) for tree in ast_
                ),
            ]
        )
