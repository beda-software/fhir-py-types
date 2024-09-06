import warnings
from typing import List as List_, Optional as Optional_, Literal as Literal_

from pydantic import PydanticDeprecatedSince20
from pydantic import (
    BaseModel as BaseModel_,
    Field,
    Extra,
    field_validator,
    ValidationError,
)
from pydantic_core import PydanticCustomError


class AnyResource(BaseModel_):
    class Config:
        extra = Extra.allow

    resourceType: str


class BaseModel(BaseModel_):
    class Config:
        extra = Extra.forbid
        validate_assignment = True
        populate_by_name = True
        defer_build = True

    def model_dump(self, *args, **kwargs):
        by_alias = kwargs.pop("by_alias", True)
        return super().model_dump(*args, **kwargs, by_alias=by_alias)

    def dict(self, *args, **kwargs):
        warnings.warn(
            "The `dict` method is deprecated; use `model_dump` instead.",
            category=PydanticDeprecatedSince20,
        )
        by_alias = kwargs.pop("by_alias", True)
        return super().model_dump(*args, **kwargs, by_alias=by_alias)

    @field_validator("*")
    @classmethod
    def validate(cls, value):
        if isinstance(value, list):
            return [
                _init_any_resource(v, index=index) for index, v in enumerate(value)
            ]
        return _init_any_resource(value)


def _init_any_resource(value, index=None):
    if isinstance(value, AnyResource):
        try:
            klass = globals().get(value.resourceType)
        except PydanticCustomError as exc:
            raise ValidationError.from_exception_data(
                "ImportError",
                [
                    {
                        "loc": [index, "resourceType"],
                        "type": "value_error",
                        "msg": f"{value.resourceType} resource is not found",
                        "input": [value],
                        "ctx": {
                            "error": f"{value.resourceType} resource is not found"
                        },
                    }
                ],
            ) from exc

        if (
            not issubclass(klass, BaseModel)
            or "resourceType" not in klass.__fields__
        ):
            raise ValidationError.from_exception_data(
                "ImportError",
                [
                    {
                        "loc": [index, "resourceType"],
                        "type": "value_error",
                        "msg": f"{value.resourceType} is not a resource",
                        "input": [value],
                        "ctx": {
                            "error": f"{value.resourceType} is not a resource"
                        },
                    }
                ],
            )

        try:
            return klass(**value.model_dump())
        except ValidationError as exc:
            raise ValidationError.from_exception_data(
                exc.title,
                [{**error, "loc": [index, *error["loc"]]} for error in exc.errors()]
                if index is not None
                else exc.errors(),
            ) from exc

    return value
