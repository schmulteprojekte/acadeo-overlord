from pydantic import BaseModel
from typing import Literal, List, Dict, Optional, Union, Any
import inspect

from src.utils.validation import ModelStringValidator


def _build_safe_execution_scope() -> dict:
    # scope to execute string with BaseModel already included
    execution_scope = {"BaseModel": BaseModel}

    # Only allow absolutely necessary builtins
    execution_scope["__builtins__"] = {
        "__build_class__": __builtins__["__build_class__"],
        "__name__": "__main__",
        "object": object,
        "dict": dict,
        "list": list,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "True": True,
        "False": False,
        "None": None,
    }

    # Add common typing modules for convenience
    execution_scope.update(
        {
            "Literal": Literal,
            "List": List,
            "Dict": Dict,
            "Optional": Optional,
            "Union": Union,
            "Any": Any,
        }
    )

    return execution_scope


def _extract_defined_pydantic_models(execution_scope) -> list:
    models = []

    for obj in execution_scope.values():
        is_class = inspect.isclass(obj)
        inherits_from_basemodel = issubclass(obj, BaseModel)
        is_not_base_model = obj is not BaseModel

        if is_class and inherits_from_basemodel and is_not_base_model:
            models.append(obj)

    return models


def transform(model_definitions_string: str) -> type[BaseModel] | None:
    """
    Dynamically executes a string containing Pydantic model definitions and
    returns the class of the last model defined or raises ValueError if the
    string contains potentially unsafe code.
    """

    ModelStringValidator.validate(
        model_definitions_string,
        model_type="BaseModel",
        definition_limit=10,
    )

    # build a minimal environment for the string to execute in
    execution_scope = _build_safe_execution_scope()

    # execute string inside safe scope
    exec(model_definitions_string, execution_scope, execution_scope)

    # filter only for pydantic basemodels defined in string
    models = _extract_defined_pydantic_models(execution_scope)

    # output last model as it would have internalized others
    return models[-1] if models else None
