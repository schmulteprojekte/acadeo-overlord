from pydantic import BaseModel, Field
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

    # add common other stuff for convenience
    execution_scope.update(
        {
            # typing
            "Literal": Literal,
            "List": List,
            "Dict": Dict,
            "Tuple": Tuple,
            "Type": Type,
            "Optional": Optional,
            "Union": Union,
            "Any": Any,
            # pydantic
            "Field": Field,
        }
    )

    return execution_scope


class _ParsingError(Exception):
    "Raised if parsing failed due to any reason."


class PydanticParser:
    @staticmethod
    def _check_if_model_is_valid(obj, valid_model_class):
        is_class = inspect.isclass(obj)
        inherits_from_model = issubclass(obj, valid_model_class)
        is_not_model_itself = obj is not valid_model_class

        is_valid_model = is_class and inherits_from_model and is_not_model_itself
        return is_valid_model

    @classmethod
    def _extract_defined_models(cls, execution_scope, model_classes: tuple[type, ...] = (BaseModel,)) -> tuple[type, ...]:
        models = []

        for obj in execution_scope.values():
            try:
                if any(cls._check_if_model_is_valid(obj, model_class) for model_class in model_classes):
                    models.append(obj)

            except TypeError:
                # skip non-class objects in the execution scope
                continue

        return tuple(models)

    @classmethod
    def parse_models(
        cls,
        definitions: str,
        model_classes: tuple[type, ...] = (BaseModel,),
    ) -> tuple[type, ...]:
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

        # build a minimal environment for the string to execute in
        execution_scope = _build_safe_execution_scope(model_classes)

        # execute string inside safe scope
        exec(definitions, execution_scope, execution_scope)

        # filter only for models that inherit from the specified model class
        models = cls._extract_defined_models(execution_scope, model_classes)

        if models:
            return models

        raise _ParsingError(f"No valid {' or '.join(mc.__name__ for mc in model_classes)} found in the provided definitions!")
