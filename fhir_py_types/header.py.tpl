from typing import (
    List as List_,
    Optional as Optional_,
    Literal as Literal_,
    Annotated as Annotated_,
    get_origin,
    get_args,
)
from pydantic import BaseModel, Field, Extra, validator, root_validator
from inspect import isclass


class PrimitiveBaseModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    def dict(self, *args, **kwargs):
        result = super().dict(*args, **kwargs)
        result.pop("value", None)
        return result


class NonPrimitiveBaseModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    @validator("*", pre=True, each_item=True)
    @classmethod
    def validate_all(cls, value, field):
        cls_type = field.outer_type_
        if (
            isclass(cls_type)
            and issubclass(cls_type, PrimitiveBaseModel)
            and not isinstance(value, PrimitiveBaseModel)
        ):
            return cls_type(value=value)
        return value

    @root_validator(pre=True)
    @classmethod
    def validate_root(cls, values):
        for field_name, field in cls.__fields__.items():
            _field_name = f"_{field_name}"
            cls_type = field.outer_type_
            isarray = False
            if get_origin(cls_type) is list:
                isarray = True
                cls_type = get_args(cls_type)[0]

            if (
                isclass(cls_type)
                and issubclass(cls_type, PrimitiveBaseModel)
                and f"_{field_name}" in values
            ):
                _value = values[_field_name]
                if field_name in values:
                    value = values[field_name]
                else:
                    value = [] if isarray else None

                if isarray:
                    values[field_name] = [
                        cls_type(value=v, **(_v if _v is not None else {}))
                        for v, _v in zip(value, _value, strict=False)
                    ]
                else:
                    values[field_name] = cls_type(value=value, **_value)
                values.pop(_field_name, None)

        return values

    def dict(self, *args, **kwargs):
        result = super().dict(*args, **kwargs)
        for field_name in self.__fields__:
            _field_name = f"_{field_name}"
            field_value = getattr(self, field_name)

            if isinstance(field_value, list):
                result[field_name] = [
                    fv.value if isinstance(fv, PrimitiveBaseModel) else fv
                    for fv in field_value
                ]
                result[_field_name] = [
                    nullable(fv.dict(*args, **kwargs))
                    if isinstance(fv, PrimitiveBaseModel)
                    else fv
                    for fv in field_value
                ]
                if all(fv is None for fv in result[field_name]):
                    result.pop(field_name, None)
                if all(fv is None for fv in result[_field_name]):
                    result.pop(_field_name, None)

            else:
                if isinstance(field_value, PrimitiveBaseModel):
                    result[field_name] = field_value.value
                    result[_field_name] = nullable(field_value.dict(*args, **kwargs))

                if result[field_name] is None:
                    result.pop(field_name, None)
                if result[_field_name] is None:
                    result.pop(_field_name, None)
        return result


def nullable(d: dict):
    if not d:
        return None
    return d

