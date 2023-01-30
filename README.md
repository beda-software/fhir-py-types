The build process is based on the standard `StructureDefintion` resource.

Basic usage scenario:
- In local environment:
    - Either
        - Download FHIR definitions in [JSON format](https://hl7.org/fhir/downloads.html) ([direct link](https://hl7.org/fhir/definitions.json.zip) at the time of writing)
        - Unzip `definitions.json/profiles-types.json` and `definitions.json/profiles-resources.json`
            - `unzip definitions.json.zip "definitions.json/profiles-types.json"`
            - `unzip definitions.json.zip "definitions.json/profiles-resources.json"`
    - Or
        - Use sh script from the `spec` folder `bash download_spec_bundle.sh` - it will download and unpack resources bundle
    - `poetry run typegen --from-bundles <path to profiles-types.json> --from-bundles <path to profiles-resources.json> --outfile <output path>`
- Or build using container:
    - `docker compose up` (will download definitions bundle, unpack and build placing the output to the `generated` folder)
- Typecheck the result:
    - `poetry run mypy <path to the generated file>`
