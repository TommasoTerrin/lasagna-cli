"""Render the JSON Schema of the registry and pipeline models."""

import json
from typing import Literal

from lasagna.core.models import Pipeline, Registry


def render_schema(kind: Literal["registry", "pipeline"]) -> str:
    model = Registry if kind == "registry" else Pipeline
    schema = model.model_json_schema(mode="validation", by_alias=True)
    return json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
