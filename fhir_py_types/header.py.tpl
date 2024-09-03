from typing import List as List_, Optional as Optional_, Literal as Literal_, Annotated as Annotated_
from pydantic import BaseModel as BaseModel_
from pydantic import Field, Extra


class BaseModel(BaseModel_):
    class Config:
        extra = Extra.forbid
        validate_assignment = True
    
    def dict(self, *args, **kwargs):
        by_alias = kwargs.pop('by_alias', True)
        return super().dict(*args, **kwargs, by_alias=by_alias)
