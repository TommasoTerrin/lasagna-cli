"""Names, references, graph shape, nesting depth and harness files."""

from lasagna_cli.issues import Issue
from lasagna_cli.model import Pipeline, Project


def check_references(project: Project) -> list[Issue]:
    """Rules R1-R14."""
    issues: list[Issue] = []
    for pipeline in project.pipelines.values():
        issues.extend(_actor_references(project, pipeline))
        issues.extend(_graph(project, pipeline))
        issues.extend(_harness_files(project, pipeline))
    issues.extend(_pipeline_nesting(project))
    return issues


def _actor_references(project: Project, pipeline: Pipeline) -> list[Issue]:
    def unknown_actor(field: str, name: str) -> Issue:
        return Issue(pipeline.file, field, f"unknown actor '{name}'")

    issues = [
        unknown_actor("trigger.by", name)
        for name in pipeline.trigger_by
        if name not in project.actors
    ]
    for phase in pipeline.phases:
        prefix = f"phases[{phase.index}]"
        if phase.actor is not None and phase.actor not in project.actors:
            issues.append(unknown_actor(f"{prefix}.actor", phase.actor))
        deciders = (
            ("trigger", phase.trigger),
            ("route", phase.route),
            ("loop.until", phase.loop.until if phase.loop else None),
        )
        for label, decider in deciders:
            if decider is not None and decider.by not in project.actors:
                issues.append(unknown_actor(f"{prefix}.{label}.by", decider.by))
        if phase.pipeline is not None and phase.pipeline not in project.pipelines:
            issues.append(
                Issue(
                    pipeline.file,
                    f"{prefix}.pipeline",
                    f"unknown pipeline '{phase.pipeline}'",
                )
            )
    return issues


def _graph(project: Project, pipeline: Pipeline) -> list[Issue]:
    issues: list[Issue] = []
    seen: set[str] = set()
    for phase in pipeline.phases:
        if phase.id in seen:
            issues.append(
                Issue(
                    pipeline.file,
                    f"phases[{phase.index}].id",
                    f"duplicate phase id '{phase.id}'",
                )
            )
        seen.add(phase.id)
    ids = {phase.id for phase in pipeline.phases}
    for phase in pipeline.phases:
        for need in phase.needs:
            if need not in ids:
                issues.append(
                    Issue(
                        pipeline.file,
                        f"phases[{phase.index}].needs",
                        f"unknown phase '{need}'",
                    )
                )
    starts = [phase for phase in pipeline.phases if not phase.needs]
    if len(starts) != 1:
        issues.append(
            Issue(
                pipeline.file,
                "phases",
                f"exactly one phase without needs is required, found {len(starts)}",
            )
        )
    cycle = _find_cycle(
        {phase.id: pipeline.children(phase.id) for phase in pipeline.phases},
        [phase.id for phase in pipeline.phases],
    )
    if cycle:
        issues.append(
            Issue(
                pipeline.file,
                "phases",
                "cycle between phases: " + " -> ".join(cycle),
            )
        )
    for phase in pipeline.phases:
        count = len(pipeline.children(phase.id))
        prefix = f"phases[{phase.index}]"
        if count > 1 and phase.route is None:
            issues.append(
                Issue(
                    pipeline.file,
                    prefix,
                    f"phase '{phase.id}' has {count} children and needs a route",
                )
            )
        if count <= 1 and phase.route is not None:
            issues.append(
                Issue(
                    pipeline.file,
                    f"{prefix}.route",
                    "route is only allowed on a phase with more than one child",
                )
            )
    return issues


def _find_cycle(edges: dict[str, list[str]], order: list[str]) -> list[str] | None:
    """First cycle found by a depth-first walk, as `[a, b, ..., a]`."""
    done: set[str] = set()
    path: list[str] = []

    def visit(node: str) -> list[str] | None:
        if node in path:
            return [*path[path.index(node) :], node]
        if node in done:
            return None
        path.append(node)
        for child in edges.get(node, ()):
            found = visit(child)
            if found:
                return found
        path.pop()
        done.add(node)
        return None

    for node in order:
        found = visit(node)
        if found:
            return found
    return None


def _harness_files(project: Project, pipeline: Pipeline) -> list[Issue]:
    base = project.root / pipeline.dir / "harness"

    def missing_skill(field: str, name: str) -> Issue | None:
        if (base / "skills" / name / "SKILL.md").is_file():
            return None
        return Issue(
            pipeline.file,
            field,
            f"missing skill '{name}' (harness/skills/{name}/SKILL.md)",
        )

    def missing_mcp(field: str, name: str) -> Issue | None:
        if (base / "mcp" / f"{name}.json").is_file():
            return None
        return Issue(
            pipeline.file,
            field,
            f"missing MCP file '{name}' (harness/mcp/{name}.json)",
        )

    found = [missing_skill("harness.skills", n) for n in pipeline.skills]
    found += [missing_mcp("harness.mcp", n) for n in pipeline.mcp]
    for phase in pipeline.phases:
        prefix = f"phases[{phase.index}].harness"
        if phase.main_skill and not (base / "phases" / phase.id / "SKILL.md").is_file():
            found.append(
                Issue(
                    pipeline.file,
                    f"{prefix}.main_skill",
                    f"missing harness/phases/{phase.id}/SKILL.md",
                )
            )
        found += [missing_skill(f"{prefix}.skills", n) for n in phase.skills]
        found += [missing_mcp(f"{prefix}.mcp", n) for n in phase.mcp]
    return [issue for issue in found if issue is not None]


def _pipeline_nesting(project: Project) -> list[Issue]:
    """R10 (cycles between pipelines) and R11 (depth against max_depth)."""
    edges = {
        name: [p.pipeline for p in pipeline.phases if p.pipeline in project.pipelines]
        for name, pipeline in project.pipelines.items()
    }
    names = sorted(project.pipelines)
    issues: list[Issue] = []
    cycle = _find_cycle(edges, names)
    if cycle:
        first = project.pipelines[cycle[0]]
        phase = next(p for p in first.phases if p.pipeline == cycle[1])
        issues.append(
            Issue(
                first.file,
                f"phases[{phase.index}].pipeline",
                "cycle between pipelines: " + " -> ".join(cycle),
            )
        )
    # Depth is only defined for pipelines that cannot reach a cycle.
    on_cycle = {n for n in names if n in _reachable(edges, edges[n])}
    unsafe = {n for n in names if on_cycle & ({n} | _reachable(edges, edges[n]))}
    depths: dict[str, int] = {}

    def depth(name: str) -> int:
        if name not in depths:
            depths[name] = max((1 + depth(c) for c in edges[name]), default=0)
        return depths[name]

    limit = project.config.max_depth
    for name in names:
        if name in unsafe or depth(name) <= limit:
            continue
        pipeline = project.pipelines[name]
        deepest = max(
            (p for p in pipeline.phases if p.pipeline in project.pipelines),
            key=lambda p: (depth(p.pipeline), -p.index),
        )
        issues.append(
            Issue(
                pipeline.file,
                f"phases[{deepest.index}].pipeline",
                f"nesting depth {depth(name)} exceeds limits.max_depth {limit}",
            )
        )
    return issues


def _reachable(edges: dict[str, list[str]], start: list[str]) -> set[str]:
    """Nodes reachable from `start`, including the start nodes themselves."""
    found: set[str] = set()
    pending = list(start)
    while pending:
        node = pending.pop()
        if node not in found:
            found.add(node)
            pending.extend(edges.get(node, ()))
    return found
