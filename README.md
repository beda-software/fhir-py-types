The build process is based on the standard `StructureDefintion` resource.

Basic usage scenario:
- Download FHIR definitions in JSON format from [the specifiction page](https://hl7.org/fhir/downloads.html) ([the direct link](https://hl7.org/fhir/definitions.json.zip) at the time of writing)
- Unzip `definitions.json/profiles-types.json` and `definitions.json/profiles-resources.json`
    - `unzip definitions.json.zip "definitions.json/profiles-types.json"`
    - `unzip definitions.json.zip "definitions.json/profiles-resources.json"`
- Generate types by:
    - `poetry run typegen --from-bundles <path to profiles-types.json> --from-bundles <path to profiles-resources.json> --outfile <output path>` from the local environment
    - `docker compose up` in a container (make sure `compose.yaml` `volumes` configuration is up to date)
- Typecheck the result:
    - `poetry run mypy <path to the generated file>`
