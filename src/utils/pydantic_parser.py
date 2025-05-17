from pydantic import BaseModel
from typing import Literal, List, Dict, Optional, Union, Any
import inspect

from src.utils.validation import ModelStringValidator


def _build_safe_execution_scope(model_class: type = BaseModel) -> dict:
    # scope to execute string with the model class already included
    execution_scope = {model_class.__name__: model_class}

    # only allow absolutely necessary builtins
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

    # add common typing modules for convenience
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


def _extract_defined_pydantic_models(execution_scope, model_class: type = BaseModel) -> list:
    models = []

    for obj in execution_scope.values():
        is_class = inspect.isclass(obj)
        try:
            inherits_from_model = issubclass(obj, model_class)
            is_not_model_itself = obj is not model_class

            if is_class and inherits_from_model and is_not_model_itself:
                models.append(obj)

        except TypeError:
            # skip non-class objects in the execution scope
            continue

    return models


def transform(model_definitions_string: str, model_class: type = BaseModel, definition_limit: int = 10) -> type | None:
    """
    Dynamically executes a string containing model definitions and
    returns the class of the last model defined or raises ValueError if the
    string contains potentially unsafe code.

    Args:
        model_definitions_string: String containing model definitions
        model_class: The base model class to use (defaults to pydantic.BaseModel)
        definition_limit: Maximum number of class definitions allowed

    Returns:
        The last defined model class or None if no models were defined
    """

    ModelStringValidator.validate(
        model_definitions_string,
        model_class=model_class,
        definition_limit=definition_limit,
    )

    # build a minimal environment for the string to execute in
    execution_scope = _build_safe_execution_scope(model_class)

    # execute string inside safe scope
    exec(model_definitions_string, execution_scope, execution_scope)

    # filter only for models that inherit from the specified model class
    models = _extract_defined_pydantic_models(execution_scope, model_class)

    # output last model as it would have internalized others
    return models[-1] if models else None
