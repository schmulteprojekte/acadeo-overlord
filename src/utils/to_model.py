from pydantic import BaseModel
from typing import Literal, List, Dict, Optional, Union, Any
import inspect, re, ast


def _validate_via_ast(model_string: str, *, model_limit: int = 10) -> bool:
    """
    Validate the model string contains only safe Pydantic model definitions using AST.

    This validates that the string:
    1. Can be parsed as valid Python code
    2. Contains only class definitions (no imports, function defs, etc)
    3. All classes inherit from BaseModel
    4. No dangerous operations like exec, eval, etc
    """

    try:
        # Parse the code into an AST
        tree = ast.parse(model_string)

        # Check if all top-level nodes are class definitions
        if not all(isinstance(node, ast.ClassDef) for node in tree.body):
            return False

        # Check number of classes
        if not tree.body or len(tree.body) > model_limit:
            return False

        # Check each class
        for node in tree.body:
            is_not_class = not isinstance(node, ast.ClassDef)
            if is_not_class:
                return False

            # Allow alphanumeric and underscore, but not dunder names
            has_invalid_name = not all(c.isalnum() or c == "_" for c in node.name) or node.name.startswith("__")
            if has_invalid_name:
                return False

            does_not_inherit_from_basemodel = not node.bases or not any(isinstance(base, ast.Name) and base.id == "BaseModel" for base in node.bases)
            if does_not_inherit_from_basemodel:
                return False

            # Check for potentially unsafe operations in class body
            for child in ast.walk(node):
                is_importing = isinstance(child, (ast.Import, ast.ImportFrom))
                if is_importing:
                    return False

                # Check for dangerous function calls, including method calls
                if isinstance(child, ast.Call):
                    dangerous_calls = ["eval", "exec", "compile", "open", "getattr", "setattr", "delattr", "globals", "locals", "__import__"]

                    # Direct function calls like eval()
                    if isinstance(child.func, ast.Name) and child.func.id in dangerous_calls:
                        return False

                    # Method calls like obj.eval()
                    if isinstance(child.func, ast.Attribute) and child.func.attr in dangerous_calls:
                        return False

                # Block access to dangerous modules and attributes
                dangerous_modules = ["os", "sys", "subprocess", "shutil"]
                dangerous_attributes = [
                    "__class__",
                    "__base__",
                    "__bases__",
                    "__subclasses__",
                    "__mro__",
                    "__dict__",
                    "__globals__",
                    "__getattribute__",
                    "__init_subclass__",
                    "__new__",
                    "__prepare__",
                    "__instancecheck__",
                ]

                if isinstance(child, ast.Attribute):
                    # Block direct module access (os.system)
                    if isinstance(child.value, ast.Name) and child.value.id in dangerous_modules:
                        return False

                    # Block dangerous dunders and attributes that can be used for sandbox escape
                    if child.attr in dangerous_attributes:
                        return False

                    # Block chained attribute access that might be sandbox escapes
                    # like obj.__class__.__bases__[0].__subclasses__()
                    if isinstance(child.value, ast.Attribute) and child.value.attr in dangerous_attributes:
                        return False

        return True

    except SyntaxError:
        # Not valid Python syntax
        return False


def _validate_model_string(model_string: str, *, model_limit: int = 10) -> bool:
    """
    Validate the model string contains only safe Pydantic model definitions
    using simple pattern matching and AST parsing.
    """

    # Quick reject based on dangerous patterns
    dangerous_patterns = [
        "import ",
        "from ",
        "exec(",
        "eval(",
        "globals(",
        "locals(",
        "getattr(",
        "setattr(",
        "delattr(",
        "compile(",
        "open(",
        "file(",
        "os.",
        "sys.",
        "subprocess.",
        "shutil.",
        "__getattribute__",
        "__init_subclass__",
    ]

    for pattern in dangerous_patterns:
        if pattern in model_string:
            return False

    # More thorough validation with AST
    return _validate_via_ast(model_string, model_limit=model_limit)


def _build_safe_execution_scope():
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
    returns the class of the last model defined or raises ValueError if the
    string contains potentially unsafe code.
    """

    if not _validate_model_string(model_definitions_string, model_limit=10):
        raise ValueError("Invalid or potentially unsafe model definition")

    execution_scope = _build_safe_execution_scope()

    # execute string inside scope
    exec(model_definitions_string, execution_scope, execution_scope)

    # filter only for pydantic basemodels defined in string
    models = _extract_defined_pydantic_models(execution_scope)

    # output last model only as it would use previous ones internally
    return models[-1] if models else None
