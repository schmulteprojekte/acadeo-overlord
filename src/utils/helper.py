from src.utils.exceptions import ClientError, ServerError

from pydantic import BaseModel, create_model
import json, uuid

from typing import Any, Optional
from langfuse.model import Prompt


def parse_sse(response):
    events = []

    for line in response.iter_lines():
        if line and line.decode("utf-8").startswith("data"):
            data_line_clean = line[5:].strip()
            data_json = json.loads(data_line_clean)
            events.append(data_json)

    return events


def gen_uuid():
    return str(uuid.uuid4())


def check_response_status(response):
    status_code = response.status_code
    response_text = response.text

    if status_code >= 500:
        raise ServerError(f"{status_code}: {response_text}")
    elif status_code >= 400:
        raise ClientError(f"{status_code}: {response_text}")


def handle_response_format(prompt, placeholders):
    json_schema = prompt.config.get("response_format")

    if isinstance(json_schema, type):
        # structured response
        return json_schema
    elif json_schema:
        # json mode
        placeholders["json_schema"] = json_schema
        return {"type": "json_object"}


def handle_messages(prompt: Prompt, placeholders: dict = None):
    compiled_prompt = prompt.compile(**placeholders)
    messages = compiled_prompt if isinstance(prompt.prompt, list) else [{"role": "user", "content": compiled_prompt}]
    return messages


def create_basemodel_from_schema(schema: dict) -> BaseModel:
    "Requires serious contemplation and testing if it should be used with langfuse."

    # Map JSON Schema types to Python (Pydantic) types
    json_type_map = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
    }

    required_fields = set(schema.get("required", []))
    properties = schema.get("properties", {})
    model_fields = {}

    for field_name, field_info in properties.items():
        # Determine Python type from JSON Schema type
        field_type_str = field_info["type"]
        py_type = json_type_map.get(field_type_str, Any)

        # If the field is required, use ellipsis (...), otherwise use None
        if field_name in required_fields:
            model_fields[field_name] = (py_type, ...)
        else:
            model_fields[field_name] = (Optional[py_type], None)

    # Dynamically create a model with the given title
    return create_model(schema["title"], **model_fields)
