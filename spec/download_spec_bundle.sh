set -e

curl --output definitions.json.zip https://hl7.org/fhir/definitions.json.zip
shasum --algorithm 256 --check bundle.checksumfile
unzip definitions.json.zip "definitions.json/profiles-types.json" "definitions.json/profiles-resources.json"
mv -v definitions.json/profiles-types.json fhir.types.json
mv -v definitions.json/profiles-resources.json fhir.resources.json

rm -rf definitions.json/
rm definitions.json.zip
