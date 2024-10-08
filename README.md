[![build status](https://github.com/beda-software/fhir-py-types/actions/workflows/static-code-analysis-and-tests.yml/badge.svg)](https://github.com/beda-software/fhir-py-types/actions/workflows/static-code-analysis-and-tests.yml)
[![Supported Python version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3110/)

## Quick start

Download `StructureDefinition` bundle and build type definitions from it:

```sh
git clone --depth 1 https://github.com/beda-software/fhir-py-types.git
cd fhir-py-types/spec/
sh download_spec_bundle.sh
cd ..
docker compose up
```

The generated type definitions can then be found in `generated/resources.py`.

## How it works

The build process is based on the standard `StructureDefintion` resource (available [in JSON format](https://hl7.org/fhir/downloads.html) from the FHIR download page, [direct link](https://hl7.org/fhir/definitions.json.zip) at the time of writing).

## Contributing

The project uses [poetry](https://github.com/python-poetry/poetry) for package management.

Type definitions can be generated by running:

```sh
poetry install
poetry run typegen --from-bundles spec/fhir.types.json --from-bundles spec/fhir.resources.json --outfile generated/resources.py
```

Where `spec/fhir.types.json` and `spec/fhir.resources.json` are bundles of `StructureDefinition` resources.

Type check definitions (the very first type checking process might take a while to complete, consecutive runs should be faster)

```sh
poetry run mypy generated/resources.py
```
