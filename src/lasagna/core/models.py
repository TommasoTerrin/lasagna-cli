"""Data models of the lasagna core."""

from dataclasses import dataclass
from typing import Annotated, Any, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _reject_extension_key(key: str) -> str:
    if key.startswith("x-"):
        raise ValueError("keys starting with 'x-' are reserved for extensions")
    return key


UserKey = Annotated[str, AfterValidator(_reject_extension_key)]


@dataclass(frozen=True)
class Finding:
    """A validation problem found in a project file."""

    rule: str
    file: str
    path: str
    message: str
    level: Literal["error", "warning"] = "error"


class _FixedKeys(BaseModel):
    """Base of the fixed-key models: `x-*` string keys are dropped before validation."""

    model_config = ConfigDict(
        extra="forbid",
        strict=True,
        json_schema_extra={"patternProperties": {"^x-": {}}},
    )

    @model_validator(mode="before")
    @classmethod
    def _drop_extension_keys(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: v
                for k, v in data.items()
                if not (isinstance(k, str) and k.startswith("x-"))
            }
        return data


class Source(_FixedKeys):
    """Where a registry pipeline was copied from."""

    from_: str = Field(alias="from")
    version: str | None = None


_NO_X_NAMES: dict[str, Any] = {"propertyNames": {"not": {"pattern": "^x-"}}}


class RegistryEntry(_FixedKeys):
    """A pipeline listed in the registry."""

    id: str
    path: str
    enabled: bool = True
    source: Source | None = None
    params: dict[UserKey, str] = Field(default={}, json_schema_extra=_NO_X_NAMES)


class Registry(_FixedKeys):
    """The `.lasagna/pipelines.yaml` file."""

    lasagna: str
    project: str | None = None
    agent_can_edit_pipelines: bool = False
    pipelines: list[RegistryEntry] = []


class Resource(_FixedKeys):
    """A resource used by a node."""

    type: str
    ref: str
    access: Literal["read", "write"] = "read"
    required: bool = True
    description: str | None = None


class Gate(_FixedKeys):
    """A gate of a node."""

    type: Literal["human", "check", "agent"]
    at: Literal["entry", "exit"] = "exit"
    message: str | None = None
    run: str | None = None
    criteria: list[str] | None = None
    by: Literal["self", "subagent"] = "self"


class Node(_FixedKeys):
    """A node of a pipeline."""

    id: str
    description: str
    name: str | None = None
    started_by: Literal["agent", "human"] = "agent"
    steps: list[str] = []
    resources: list[Resource] = []
    gate: Gate | None = None


class DirectEdge(_FixedKeys):
    """A direct edge between two nodes."""

    type: Literal["direct"]
    from_: str = Field(alias="from")
    to: str


class LoopEdge(_FixedKeys):
    """A loop edge: goes back to an earlier node, a bounded number of times."""

    type: Literal["loop"]
    from_: str = Field(alias="from")
    to: str
    when: str = "fail"
    max_iterations: int


class Route(_FixedKeys):
    """A route of a router edge."""

    to: str
    when: str | None = None
    run: str | None = None


class RouterEdge(_FixedKeys):
    """A router edge: picks one of several routes."""

    type: Literal["router"]
    from_: str = Field(alias="from")
    decided_by: Literal["agent", "human", "check"]
    routes: list[Route]
    default: str | None = None


Edge = Annotated[DirectEdge | LoopEdge | RouterEdge, Field(discriminator="type")]


class ParamDef(_FixedKeys):
    """A parameter definition of a pipeline."""

    default: str
    description: str | None = None


class InputDef(_FixedKeys):
    """An input definition of a pipeline."""

    description: str | None = None
    required: bool = True


class OutputDef(_FixedKeys):
    """An output definition of a pipeline."""

    description: str | None = None


class Pipeline(_FixedKeys):
    """A `pipeline.yaml` file."""

    lasagna: str
    id: str
    entry: str | None = None
    nodes: list[Node]
    name: str | None = None
    version: str | None = None
    description: str | None = None
    params: dict[UserKey, ParamDef] = Field(default={}, json_schema_extra=_NO_X_NAMES)
    inputs: dict[UserKey, InputDef] = Field(default={}, json_schema_extra=_NO_X_NAMES)
    outputs: dict[UserKey, OutputDef] = Field(default={}, json_schema_extra=_NO_X_NAMES)
    edges: list[Edge] = []
