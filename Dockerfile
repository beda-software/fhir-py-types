FROM python:3.11

RUN addgroup --gid 1000 dockeruser
RUN adduser --disabled-login --uid 1000 --gid 1000 dockeruser
RUN mkdir -p /app/spec
RUN chown -R dockeruser:dockeruser /app/

RUN pip install poetry

USER dockeruser

COPY pyproject.toml poetry.lock /app/
COPY fhir_py_types /app/fhir_py_types
WORKDIR /app

RUN poetry install

CMD ["poetry", "run", "typegen", "--from-bundles", "/app/spec/fhir.types.json", "--from-bundles", "/app/spec/fhir.resources.json", "--outfile", "/app/generated/resources.py"]
