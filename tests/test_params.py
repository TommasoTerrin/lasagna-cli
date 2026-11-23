import pytest

from lasagna_cli.model import Actor, AgentCommands, Param
from lasagna_cli.params import (
    MissingParamError,
    UnknownParamError,
    param_env,
    resolve_params,
)
from lasagna_cli.resolve import Scope, UnresolvedError


def agent(
    params: dict[str, Param] | None = None, models: dict[str, str] | None = None
) -> Actor:
    return Actor(
        name="claude",
        type="agent",
        file=".lasagna/actors/claude.yaml",
        params=params
        if params is not None
        else {
            "prompt": Param(required=True, default=None),
            "model": Param(required=False, default="large"),
        },
        models=models if models is not None else {"large": "opus", "small": "haiku"},
        commands=AgentCommands(
            check=(), inject=None, run="true", run_interactive=None, cleanup=None
        ),
    )


def scope(**kwargs) -> Scope:
    return Scope(
        pipeline_inputs=kwargs.pop("pipeline_inputs", {}),
        phase_outputs=kwargs.pop("phase_outputs", {}),
        **kwargs,
    )


def test_values_are_resolved_from_the_scope() -> None:
    result = resolve_params(
        agent(),
        {"prompt": "do ${{ inputs.x }} for ${{ pipeline.inputs.y }}"},
        scope(inputs={"x": "one"}, pipeline_inputs={"y": "two"}),
    )
    assert result["prompt"] == "do one for two"


def test_a_default_fills_a_param_that_was_not_passed() -> None:
    actor = agent(
        {
            "prompt": Param(required=True, default=None),
            "effort": Param(required=False, default="low"),
        },
        models={},
    )
    assert resolve_params(actor, {"prompt": "p"}, scope()) == {
        "prompt": "p",
        "effort": "low",
    }


def test_the_model_alias_is_replaced_by_the_real_id() -> None:
    result = resolve_params(agent(), {"prompt": "p", "model": "large"}, scope())
    assert result["model"] == "opus"


def test_an_unknown_model_passes_through_unchanged() -> None:
    result = resolve_params(agent(), {"prompt": "p", "model": "custom-1"}, scope())
    assert result["model"] == "custom-1"


def test_the_default_model_goes_through_the_alias_too() -> None:
    assert resolve_params(agent(), {"prompt": "p"}, scope())["model"] == "opus"


def test_a_missing_required_param_is_an_error() -> None:
    with pytest.raises(MissingParamError) as caught:
        resolve_params(agent(), {}, scope())
    assert caught.value.name == "prompt"


def test_a_param_the_actor_does_not_declare_is_an_error() -> None:
    with pytest.raises(UnknownParamError) as caught:
        resolve_params(agent(), {"prompt": "p", "colour": "red"}, scope())
    assert caught.value.name == "colour"


def test_an_unresolvable_value_raises() -> None:
    with pytest.raises(UnresolvedError):
        resolve_params(agent(), {"prompt": "${{ inputs.nope }}"}, scope(inputs={}))


def test_a_resolved_value_is_not_resolved_twice() -> None:
    result = resolve_params(
        agent(),
        {"prompt": "${{ inputs.x }}"},
        scope(inputs={"x": "${{ pipeline.inputs.y }}"}, pipeline_inputs={"y": "no"}),
    )
    assert result["prompt"] == "${{ pipeline.inputs.y }}"


def test_param_env_names() -> None:
    assert param_env({"prompt": "p", "max-tokens": "5"}) == {
        "LASAGNA_PARAM_PROMPT": "p",
        "LASAGNA_PARAM_MAX_TOKENS": "5",
    }
