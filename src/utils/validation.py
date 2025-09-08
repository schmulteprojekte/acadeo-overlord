import ast
from pydantic import BaseModel


class _Dangers(BaseModel):
    """Container for dangerous operations and patterns."""

    calls: tuple[str, ...] = ()
    modules: tuple[str, ...] = ()
    attributes: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()


class _AbstractSyntaxTreeValidator:
    """Class for validating Python code safety using Abstract Syntax Tree analysis."""

    DANGERS = _Dangers(
        calls=(
            "eval",
            "exec",
            "compile",
            "open",
            "getattr",
            "setattr",
            "delattr",
            "globals",
            "locals",
            "__import__",
        ),
        modules=(
            "os",
            "sys",
            "subprocess",
            "shutil",
        ),
        attributes=(
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
        ),
    )

    @classmethod
    def _has_dangerous_attribute(cls, child) -> bool:
        if not isinstance(child, ast.Attribute):
            return False

        # block direct module access (os.system)
        if isinstance(child.value, ast.Name):
            if child.value.id in cls.DANGERS.modules:
                return True

        # block dangerous dunders and attributes that can be used for sandbox escape
        is_dangerous_attr = child.attr in cls.DANGERS.attributes
        if is_dangerous_attr:
            return True

        # block chained attribute access that might be sandbox escapes
        # like obj.__class__.__bases__[0].__subclasses__()
        if isinstance(child.value, ast.Attribute):
            is_dangerous_chain = child.value.attr in cls.DANGERS.attributes
            if is_dangerous_chain:
                return True

        return False

    @classmethod
    def _has_dangerous_call(cls, child) -> bool:
        if not isinstance(child, ast.Call):
            return False

        # direct function calls like eval()
        if isinstance(child.func, ast.Name):
            return child.func.id in cls.DANGERS.calls

        # method calls like obj.eval()
        if isinstance(child.func, ast.Attribute):
            return child.func.attr in cls.DANGERS.calls

        return False

    @staticmethod
    def _is_import(child) -> bool:
        return isinstance(child, (ast.Import, ast.ImportFrom))

    @classmethod
    def _is_safe_class_body(cls, node) -> bool:
        for child in ast.walk(node):
            if cls._is_import(child):
                return False

            if cls._has_dangerous_call(child):
                return False

            if cls._has_dangerous_attribute(child):
                return False

        return True

    # --

    @staticmethod
    def _uses_only_allowed_models(node, allowed_models: tuple[type, ...]) -> bool:
        if not isinstance(allowed_models, tuple):
            allowed_models = (allowed_models,)

        has_bases = bool(node.bases)
        if not has_bases:
            return False

        _allowed_model_names = {model.__name__ for model in allowed_models}
        inherits_from_allowed_model = any(isinstance(base, ast.Name) and base.id in _allowed_model_names for base in node.bases)
        return inherits_from_allowed_model

    @staticmethod
    def _is_valid_class_name(node) -> bool:
        is_alphanumeric_plus_underscore = all(c.isalnum() or c == "_" for c in node.name)
        might_be_dunder = node.name.startswith("__") or node.name.endswith("__")
        return is_alphanumeric_plus_underscore and not might_be_dunder

    @staticmethod
    def _is_class_definition(node) -> bool:
        return isinstance(node, ast.ClassDef)

    @staticmethod
    def _is_in_definition_limit(tree, definition_limit: int) -> bool:
        has_definitions = bool(tree.body)
        within_limit = len(tree.body) <= definition_limit
        return has_definitions and within_limit

    # --

    @classmethod
    def validate(cls, definitions: str, allowed_models: tuple[type, ...], definition_limit: int) -> bool:
        """
        Validate the model string contains only safe Pydantic model definitions using AST.

        This validates that the string:
        1. Can be parsed as valid Python code
        2. Contains only class definitions (no imports, function defs, etc)
        3. All classes inherit from BaseModel
        4. No dangerous operations like exec, eval, etc
        """

        try:
            tree = ast.parse(definitions)

            if not cls._is_in_definition_limit(tree, definition_limit):
                return False

            for node in tree.body:
                if not cls._is_class_definition(node):
                    return False
                if not cls._is_valid_class_name(node):
                    return False
                if not cls._uses_only_allowed_models(node, allowed_models):
                    return False
                if not cls._is_safe_class_body(node):
                    return False

            return True

        except SyntaxError:
            # not valid Python syntax
            return False


class _PatternValidator:
    """Validate the model string using simple pattern matching."""

    DANGERS = _Dangers(
        patterns=(
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
        )
    )

    @classmethod
    def validate(cls, model_string: str) -> bool:
        """Validate the model string contains no dangerous patterns."""

        for pattern in cls.DANGERS.patterns:
            if pattern in model_string:
                return False
        return True


class _ValidationError(Exception):
    "Raised if validation failed due to any reason."


class StringValidator:
    """
    Wraps other validators offering ways to validate whether python code
    in string form contains only code that is safe based on your settings.
    """

    @staticmethod
    def basic_pattern_validation(definitions):
        if not _PatternValidator.validate(definitions):
            raise _ValidationError("Invalid or potentially unsafe pattern detected in model definition")

    @staticmethod
    def validate_models(definitions: str, *, allowed_models: tuple[type, ...] = (BaseModel,), definition_limit: int = 10):
        if not _AbstractSyntaxTreeValidator.validate(definitions, allowed_models, definition_limit):
            raise _ValidationError("Invalid or potentially unsafe code structure in model definition")

    @classmethod
    def validate(cls, value, allowed_models: tuple[type, ...] = (BaseModel,), definition_limit: int = 10):
        "Wrapper for all methods chained."

        cls.basic_pattern_validation(value)
        cls.validate_models(value, allowed_models=allowed_models, definition_limit=definition_limit)


# class InputValidator:
#     "Toolbox for all input validation needs."

#     @property (must be used on instance not class)
#     def strings(cls):
#         return StringValidator
