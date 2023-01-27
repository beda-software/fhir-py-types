FROM python:3.11

RUN addgroup --gid 1000 dockeruser
RUN adduser --disabled-login --uid 1000 --gid 1000 dockeruser
RUN mkdir -p /app/spec
RUN chown -R dockeruser:dockeruser /app/

RUN pip install poetry

USER dockeruser

COPY spec/bundle.checksumfile /app/spec/
WORKDIR /app/spec
RUN curl --silent --show-error --output definitions.json.zip https://hl7.org/fhir/definitions.json.zip
RUN shasum -a 256 -c bundle.checksumfile -q
RUN unzip definitions.json.zip "definitions.json/profiles-types.json" "definitions.json/profiles-resources.json"
RUN mv definitions.json/profiles-types.json fhir.types.json
RUN mv definitions.json/profiles-resources.json fhir.resources.json

COPY pyproject.toml poetry.lock /app/
COPY fhir_py_types /app/fhir_py_types
WORKDIR /app

RUN poetry install

CMD ["poetry", "run", "typegen", "--from-bundles", "/app/spec/fhir.types.json", "--from-bundles", "/app/spec/fhir.resources.json", "--outfile", "/app/generated/resources.py"]
