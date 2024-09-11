from typing import (
    List as List_,
    Optional as Optional_,
    Literal as Literal_,
    Any as Any_,
)

from pydantic import (
    BaseModel as BaseModel_,
    ConfigDict,
    Field,
    SerializationInfo,
    field_validator,
    field_serializer,
    ValidationError,
)
from pydantic.main import IncEx
from pydantic_core import PydanticCustomError


class AnyResource(BaseModel_):
    model_config = ConfigDict(extra="allow")

    resourceType: str


class BaseModel(BaseModel_):
    model_config = ConfigDict(
        # Extra attributes are disabled because fhir does not allow it
        extra="forbid",
        # Validation are applied while mutating the resource
        validate_assignment=True,
        # It's important for reserved keywords population in constructor (e.g. for_)
        populate_by_name=True,
        # Speed up initial load by lazy build
        defer_build=True,
        # It does not break anything, just for convinience
        coerce_numbers_to_str=True,
    )

    def model_dump(
        self,
        *,
        mode: Literal_["json", "python"] | str = "python",
        include: IncEx = None,
        exclude: IncEx = None,
        context: Any_ | None = None,
        by_alias: bool = True,
        exclude_unset: bool = False,
        exclude_defaults: bool = False,
        exclude_none: bool = True,
        round_trip: bool = False,
        warnings: bool | Literal_["none", "warn", "error"] = True,
        serialize_as_any: bool = False,
    ):
        # Override default parameters for by_alias and exclude_none preserving function declaration
        return super().model_dump(
            mode=mode,
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            round_trip=round_trip,
            warnings=warnings,
            serialize_as_any=serialize_as_any,
        )

    @field_serializer("*")
    @classmethod
    def serialize_all_fields(cls, value: Any_, info: SerializationInfo):
        if isinstance(value, list):
            return [_serialize(v, info) for v in value]

        return _serialize(value, info)

    @field_validator("*")
    @classmethod
    def validate_all_fields(cls, value: Any_):
        if isinstance(value, list):
            return [_validate(v, index=index) for index, v in enumerate(value)]
        return _validate(value)


def _serialize(value: Any_, info: SerializationInfo):
    # Custom serializer for AnyResource fields
    kwargs = {
        "mode": info.mode,
        "include": info.include,
        "exclude": info.exclude,
        "context": info.context,
        "by_alias": info.by_alias,
        "exclude_unset": info.exclude_unset,
        "exclude_defaults": info.exclude_defaults,
        "exclude_none": info.exclude_none,
        "round_trip": info.round_trip,
        "serialize_as_any": info.serialize_as_any,
    }
    if isinstance(value, AnyResource):
        return value.model_dump(**kwargs)  # type: ignore
    if isinstance(value, BaseModel_):
        return value.model_dump(**kwargs)  # type: ignore
    return value


def _validate(value: Any_, index: int | None = None):
    # Custom validator for AnyResource fields
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
                        "ctx": {"error": f"{value.resourceType} resource is not found"},
                    }
                ],
            ) from exc

        if not issubclass(klass, BaseModel) or "resourceType" not in klass.__fields__:
            raise ValidationError.from_exception_data(
                "ImportError",
                [
                    {
                        "loc": [index, "resourceType"],
                        "type": "value_error",
                        "msg": f"{value.resourceType} is not a resource",
                        "input": [value],
                        "ctx": {"error": f"{value.resourceType} is not a resource"},
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