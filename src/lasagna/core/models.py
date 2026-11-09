"""Data models of the lasagna core."""

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


@dataclass(frozen=True)
class Finding:
    """A validation problem found in a project file."""

    rule: str
    file: str
    path: str
    message: str
    level: Literal["error", "warning"] = "error"


class RegistryEntry(BaseModel):
    """A pipeline listed in the registry."""

    model_config = ConfigDict(extra="forbid")

    id: str
    path: str
    enabled: bool = True


class Registry(BaseModel):
    """The `.lasagna/pipelines.yaml` file."""

    model_config = ConfigDict(extra="forbid")

    lasagna: str
    project: str | None = None
    agent_can_edit_pipelines: bool = False
    pipelines: list[RegistryEntry] = []


class Node(BaseModel):
    """A node of a pipeline."""

    model_config = ConfigDict(extra="forbid")

    id: str
    name: str | None = None
    description: str | None = None


class Edge(BaseModel):
    """A direct edge between two nodes."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    type: Literal["direct"]
    from_: str = Field(alias="from")
    to: str


class Pipeline(BaseModel):
    """A `pipeline.yaml` file."""

    model_config = ConfigDict(extra="forbid")

    lasagna: str
    id: str
    entry: str
    nodes: list[Node]
    edges: list[Edge] = []
    name: str | None = None
    description: str | None = None
    version: str | None = None
