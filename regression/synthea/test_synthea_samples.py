import json
import os
import random
from collections.abc import Generator

import pytest

from generated.resources import Bundle

NUMBER_OF_SAMPLES_TO_VALIDATE = 10


def iterate_synthea_bundles() -> Generator[str]:
    directory = os.path.join(os.path.dirname(__file__), "./fhir/")
    directory_content = random.sample(
        [path for path in os.listdir(directory) if path.endswith(".json")],
        NUMBER_OF_SAMPLES_TO_VALIDATE,
    )
    for filename in directory_content:
        yield os.path.join(directory, filename)


@pytest.mark.parametrize("bundle_filepath", iterate_synthea_bundles())
def test_can_parse_and_validate_samples_bundle(bundle_filepath: str) -> None:
    with open(bundle_filepath, "rb") as bundle_file:
        original = json.loads(bundle_file.read())
        bundle = Bundle.model_validate(original)
        assert bundle.model_dump() == original
