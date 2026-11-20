"""Semantic rules of PROTOCOL section 10 that go beyond the schemas."""

import re

from lasagna_cli.issues import Issue
from lasagna_cli.model import Project
from lasagna_cli.schemas import primitive_copy_warnings
from lasagna_cli.validation.actors import check_actors
from lasagna_cli.validation.expr_rules import check_expressions
from lasagna_cli.validation.references import check_references


def validate_project(project: Project) -> list[Issue]:
    """Return the load issues plus every rule violation, sorted for display."""
    issues = [
        *project.issues,
        *check_references(project),
        *check_actors(project),
        *check_expressions(project),
        *primitive_copy_warnings(project.root),
    ]
    return sorted(issues, key=lambda i: (_natural(i.file), _natural(i.field)))


def _natural(text: str) -> list[str | int]:
    """Sort key where digit runs compare as numbers: phases[2] < phases[10]."""
    return [int(p) if p.isdigit() else p for p in re.split(r"(\d+)", text)]
