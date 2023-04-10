import json
import os

import pytest

from generated.resources import Bundle


def iterate_synthea_bundles():
    directory = os.path.join(os.path.dirname(__file__), "./fhir/")
    for filename in os.listdir(directory):
        if filename.endswith(".json"):
            yield os.path.join(directory, filename)


@pytest.mark.parametrize("bundle_filepath", iterate_synthea_bundles())
def test_can_parse_and_validate_samples_bundle(bundle_filepath: str):
    with open(bundle_filepath, "rb") as bundle_file:
        Bundle.parse_obj(json.loads(bundle_file.read()))
