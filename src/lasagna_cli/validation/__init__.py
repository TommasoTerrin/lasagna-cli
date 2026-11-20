"""Semantic rules of PROTOCOL section 10 that go beyond the schemas."""

from lasagna_cli.issues import Issue
from lasagna_cli.model import Project
from lasagna_cli.validation.actors import check_actors
from lasagna_cli.validation.references import check_references


def validate_project(project: Project) -> list[Issue]:
    """Return the load issues plus every rule violation, sorted for display."""
    issues = [*project.issues, *check_references(project), *check_actors(project)]
    return sorted(issues, key=lambda issue: (issue.file, issue.field))
