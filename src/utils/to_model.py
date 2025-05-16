from pydantic import BaseModel
from typing import Literal
import inspect


def _extract_defined_pydantic_models(execution_scope):
    models = []

    for obj in execution_scope.values():
        is_class = inspect.isclass(obj)
        inherits_from_basemodel = issubclass(obj, BaseModel)
        is_not_base_model = obj is not BaseModel

        if is_class and inherits_from_basemodel and is_not_base_model:
            models.append(obj)

    return models


def transform(model_definitions_string: str):
    """
    Dynamically executes a string containing Pydantic model definitions and
    returns the class of the last model defined.

    The execution scope can be extended with common types if needed:

    ```python
    from typing import List, Dict, Union
    import datetime

    execution_scope.update({"List": List, "Dict": Dict, "Union": Union})
    execution_scope["datetime"] = datetime
    ```
    """

    # place to execute string
    execution_scope = {}

    # make stuff available to execution
    execution_scope["BaseModel"] = BaseModel
    execution_scope["Literal"] = Literal

    # execute string inside scope
    exec(model_definitions_string, execution_scope, execution_scope)

    # filter only for pydantic basemodels defined in string
    models = _extract_defined_pydantic_models(execution_scope)

    # output last model only as it would use previous ones internally
    return models[-1] if models else None
