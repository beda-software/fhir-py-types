from abc import ABC
from inspect import isclass
from types import UnionType
from typing import (
    Any,
    Union,
    get_args,
    get_origin,
    Annotated as Annotated_,
    List as List_,
    Literal as Literal_,
    Optional as Optional_,
)

from pydantic import BaseModel, Extra, Field, root_validator, validator


class PrimitiveBaseModel(BaseModel, ABC, extra=Extra.forbid, validate_assignment=True):
    value: Any

    def dict(self, *args, **kwargs):
        result = super().dict(*args, **kwargs)
        result.pop("value", None)
        return result

    def __eq__(self, other) -> bool:
        if isinstance(other, PrimitiveBaseModel):
            return self.value == other.value
        return self.value == other

    def __lt__(self, other) -> bool:
        if isinstance(other, PrimitiveBaseModel):
            return self.value < other.value
        return self.value < other

    def __le__(self, other) -> bool:
        if isinstance(other, PrimitiveBaseModel):
            return self.value <= other.value
        return self.value <= other

    def __gt__(self, other) -> bool:
        if isinstance(other, PrimitiveBaseModel):
            return self.value > other.value
        return self.value > other

    def __ge__(self, other) -> bool:
        if isinstance(other, PrimitiveBaseModel):
            return self.value >= other.value
        return self.value >= other

    def __str__(self):
        return str(self.value)

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)

    def __bool__(self):
        return bool(self.value)


class NonPrimitiveBaseModel(BaseModel, extra=Extra.forbid, validate_assignment=True):
    @validator("*", pre=True, each_item=True)
    @classmethod
    def validate_all(cls, value, field):
        cls_type, _isarray = get_primitive_cls_type(field.outer_type_)

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
            cls_type, isarray = get_primitive_cls_type(field.outer_type_)
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


def get_primitive_cls_type(cls_type):
    isarray = False
    if get_origin(cls_type) is list:
        isarray = True
        cls_type = get_args(cls_type)[0]

    if get_origin(cls_type) is UnionType or get_origin(cls_type) is Union:
        cls_type = get_args(cls_type)[0]

    return cls_type, isarray


def nullable(d: dict):
    if not d:
        return None
    return d
