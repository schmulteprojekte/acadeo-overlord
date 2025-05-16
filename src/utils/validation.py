import ast


class Validator:
    DANGERS = dict(
        patterns=[
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
        ],
        calls=[
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
        ],
        modules=[
            "os",
            "sys",
            "subprocess",
            "shutil",
        ],
        attributes=[
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
        ],
    )

    @classmethod
    def _validate_ast(cls, model_string: str, model_limit: int) -> bool:
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
                        # Direct function calls like eval()
                        if isinstance(child.func, ast.Name) and child.func.id in cls.DANGERS["calls"]:
                            return False

                        # Method calls like obj.eval()
                        if isinstance(child.func, ast.Attribute) and child.func.attr in cls.DANGERS["calls"]:
                            return False

                    # Block access to dangerous modules and attributes
                    if isinstance(child, ast.Attribute):
                        # Block direct module access (os.system)
                        if isinstance(child.value, ast.Name) and child.value.id in cls.DANGERS["modules"]:
                            return False

                        # Block dangerous dunders and attributes that can be used for sandbox escape
                        if child.attr in cls.DANGERS["attributes"]:
                            return False

                        # Block chained attribute access that might be sandbox escapes
                        # like obj.__class__.__bases__[0].__subclasses__()
                        if isinstance(child.value, ast.Attribute) and child.value.attr in cls.DANGERS["attributes"]:
                            return False

            return True

        except SyntaxError:
            # Not valid Python syntax
            return False

    @classmethod
    def _validate_patterns(cls, model_string: str) -> bool:
        "Validate the model string contains only safe Pydantic model definitions using simple pattern matching."

        # Quick reject based on dangerous patterns
        for pattern in cls.DANGERS["patterns"]:
            if pattern in model_string:
                return False
        return True

    @classmethod
    def validate(cls, model_string, *, model_limit: int = 10):
        has_only_safe_patterns = cls._validate_patterns(model_string)
        is_safe_based_on_ast = cls._validate_ast(model_string, model_limit)

        if not has_only_safe_patterns or not is_safe_based_on_ast:
            raise ValueError("Invalid or potentially unsafe model definition")
