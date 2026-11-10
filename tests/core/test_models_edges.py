import pytest

from lasagna.core.validate import validate_project

RF = ".lasagna/pipelines.yaml"
PF = ".lasagna/pipelines/demo/pipeline.yaml"

R0 = {"lasagna": "3.0", "pipelines": [{"id": "demo", "path": "pipelines/demo"}]}
P0 = {
    "lasagna": "3.0",
    "id": "demo",
    "entry": "a",
    "nodes": [{"id": "a", "description": "A"}, {"id": "b", "description": "B"}],
    "edges": [{"type": "direct", "from": "a", "to": "b"}],
}

LOOP = {"type": "loop", "from": "b", "to": "a"}


def _loop(**fields):
    return {**LOOP, **fields}


# AC-V3-005
@pytest.mark.parametrize(
    ("edge", "expected"),
    [
        pytest.param(_loop(max_iterations=3), [], id="default-when"),
        pytest.param(_loop(max_iterations=3, when="fail"), [], id="when-fail"),
        pytest.param(_loop(max_iterations=3, when="pass"), [], id="when-pass"),
        pytest.param(
            _loop(max_iterations=3, when="free text condition"), [], id="when-free-text"
        ),
        pytest.param(_loop(max_iterations=0), [], id="zero-is-not-a-model-concern"),
        pytest.param(LOOP, [("V01", PF, "edges[1].max_iterations")], id="missing-max"),
        pytest.param(
            _loop(max_iterations="3"),
            [("V01", PF, "edges[1].max_iterations")],
            id="max-string",
        ),
        pytest.param(
            _loop(max_iterations=True),
            [("V01", PF, "edges[1].max_iterations")],
            id="max-bool",
        ),
        pytest.param(
            _loop(max_iterations=2.5),
            [("V01", PF, "edges[1].max_iterations")],
            id="max-float",
        ),
        pytest.param(
            _loop(max_iterations=3, when=None),
            [("V01", PF, "edges[1].when")],
            id="when-null",
        ),
    ],
)
def test_loop_edge_requires_an_integer_max_iterations_and_accepts_any_when_text(
    edge, expected
):
    pipeline = {**P0, "edges": [*P0["edges"], edge]}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


def _router(**fields):
    base = {
        "type": "router",
        "from": "a",
        "decided_by": "agent",
        "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}],
        "default": "b",
    }
    base.update(fields)
    return {k: v for k, v in base.items() if v is not _ABSENT}


_ABSENT = object()


# AC-V3-005
@pytest.mark.parametrize(
    ("edge", "expected"),
    [
        pytest.param(_router(), [], id="agent-with-when-routes"),
        pytest.param(_router(decided_by="human"), [], id="decided-by-human"),
        pytest.param(
            _router(decided_by="check", routes=[{"run": "r", "to": "b"}]),
            [],
            id="decided-by-check-with-run-route",
        ),
        pytest.param(_router(default=_ABSENT), [], id="no-default"),
        pytest.param(_router(routes=[]), [], id="empty-routes-is-not-a-model-concern"),
        pytest.param(
            _router(decided_by="robot"),
            [("V01", PF, "edges[1].decided_by")],
            id="unknown-decided-by",
        ),
        pytest.param(
            _router(routes=_ABSENT),
            [("V01", PF, "edges[1].routes")],
            id="missing-routes",
        ),
        pytest.param(
            _router(routes=[{"when": "w"}, {"when": "w2", "to": "a"}]),
            [("V01", PF, "edges[1].routes[0].to")],
            id="route-without-to",
        ),
        pytest.param(
            _router(routes=[{"when": "w", "to": "b"}, {"when": 3, "to": "a"}]),
            [("V01", PF, "edges[1].routes[1].when")],
            id="route-when-not-a-string",
        ),
    ],
)
def test_router_edge_accepts_any_route_list_and_rejects_malformed_decisions_and_routes(
    edge, expected
):
    pipeline = {**P0, "edges": [*P0["edges"], edge]}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == expected


_ROUTER_OK = {
    "type": "router",
    "from": "a",
    "decided_by": "agent",
    "routes": [{"when": "w", "to": "b"}, {"when": "w2", "to": "a"}],
}
_LOOP_OK = {"type": "loop", "from": "b", "to": "a", "max_iterations": 3}


# AC-V3-005
@pytest.mark.parametrize(
    ("edges", "expected_path"),
    [
        pytest.param(
            [{**P0["edges"][0], "when": "fail"}], "edges[0].when", id="direct-with-when"
        ),
        pytest.param(
            [{**P0["edges"][0], "max_iterations": 1}],
            "edges[0].max_iterations",
            id="direct-with-max-iterations",
        ),
        pytest.param(
            [*P0["edges"], {**_ROUTER_OK, "to": "b"}],
            "edges[1].to",
            id="router-with-to",
        ),
        pytest.param(
            [*P0["edges"], {**_LOOP_OK, "routes": []}],
            "edges[1].routes",
            id="loop-with-routes",
        ),
    ],
)
def test_an_edge_key_belonging_to_another_edge_type_is_unknown(edges, expected_path):
    pipeline = {**P0, "edges": edges}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [("V01", PF, expected_path)]


# AC-V3-005
@pytest.mark.parametrize(
    "edge",
    [
        pytest.param({"type": "teleport", "from": "a", "to": "b"}, id="unknown-type"),
        pytest.param({"from": "a", "to": "b"}, id="missing-type"),
        pytest.param({"type": 3, "from": "a", "to": "b"}, id="type-not-a-string"),
    ],
)
def test_an_edge_with_a_missing_or_unknown_type_is_reported_on_its_type_key(edge):
    pipeline = {**P0, "edges": [edge]}

    findings = validate_project(R0, {"pipelines/demo": pipeline})

    assert [(f.rule, f.file, f.path) for f in findings] == [
        ("V01", PF, "edges[0].type")
    ]


# AC-V3-005
@pytest.mark.parametrize(
    ("registry", "pipeline", "expected"),
    [
        pytest.param(
            R0,
            {**P0, "edges": [{"type": "direct", "from_": "a", "to": "b"}]},
            [("V01", PF, "edges[0].from"), ("V01", PF, "edges[0].from_")],
            id="edge-from-underscore",
        ),
        pytest.param(
            {
                **R0,
                "pipelines": [{**R0["pipelines"][0], "source": {"from_": "x"}}],
            },
            P0,
            [
                ("V01", RF, "pipelines[0].source.from"),
                ("V01", RF, "pipelines[0].source.from_"),
            ],
            id="source-from-underscore",
        ),
    ],
)
def test_the_python_attribute_name_from_underscore_is_not_accepted_in_place_of_from(
    registry, pipeline, expected
):
    findings = validate_project(registry, {"pipelines/demo": pipeline})

    assert sorted((f.rule, f.file, f.path) for f in findings) == sorted(expected)
