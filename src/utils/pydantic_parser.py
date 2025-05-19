from pydantic import BaseModel
from typing import Literal, List, Dict, Tuple, Type, Optional, Union, Any
import inspect

from src.utils import validation


def _build_safe_execution_scope(model_classes: tuple[type, ...] = (BaseModel,)) -> dict:
    # scope to execute string with the model class already included
    execution_scope = {model_class.__name__: model_class for model_class in model_classes}

    # only allow certain built-in types
    execution_scope["__builtins__"] = {
        # absolutely necessary
        "__build_class__": __builtins__["__build_class__"],
        "__name__": "__main__",
        # types and hints
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
            "Tuple": Tuple,
            "Type": Type,
            "Optional": Optional,
            "Union": Union,
            "Any": Any,
        }
    )

    return execution_scope


def _extract_defined_pydantic_models(execution_scope, model_classes: tuple[type, ...] = (BaseModel,)) -> tuple[type, ...]:
    models = []

    for obj in execution_scope.values():
        is_class = inspect.isclass(obj)

        try:

            def check_if_model_is_valid(model_class):
                inherits_from_model = issubclass(obj, model_class)
                is_not_model_itself = obj is not model_class

                is_valid_model = is_class and inherits_from_model and is_not_model_itself
                return is_valid_model

            if any(check_if_model_is_valid(model_class) for model_class in model_classes):
                models.append(obj)

        except TypeError:
            # skip non-class objects in the execution scope
            continue

    return tuple(models)


class ParsingError(Exception):
    "Raised if parsing failed due to any reason."


def parse_models(definitions: str, model_classes: tuple[type, ...] = (BaseModel,), definition_limit: int = 10) -> tuple[type, ...]:
    """
    Dynamically executes a string containing model definitions and
    returns defined model classes in a tuple or raises ValueError if the
    string contains potentially unsafe code.

    Args:
        model_definitions_string: String containing model definitions
        model_class: The base model class to use (defaults to pydantic.BaseModel)
        definition_limit: Maximum number of class definitions allowed

    Returns:
        The last defined model class or None if no models were defined
    """

    if not isinstance(model_classes, tuple):
        model_classes = (model_classes,)

    validation.StringValidator.validate(definitions, model_classes, definition_limit)

    # build a minimal environment for the string to execute in
    execution_scope = _build_safe_execution_scope(model_classes)

    # execute string inside safe scope
    exec(definitions, execution_scope, execution_scope)

    # filter only for models that inherit from the specified model class
    models = _extract_defined_pydantic_models(execution_scope, model_classes)

    if models:
        return models

    raise ParsingError(f"No valid {' or '.join(mc.__name__ for mc in model_classes)} found in the provided definitions!")
