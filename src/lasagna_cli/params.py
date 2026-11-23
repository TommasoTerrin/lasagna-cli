"""What an agent receives: `with` values resolved, defaults filled, model alias."""

from collections.abc import Mapping

from lasagna_cli.model import Actor
from lasagna_cli.resolve import Scope, resolve_text


class MissingParamError(Exception):
    """A required param of the actor was not provided."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"missing required param '{name}'")


class UnknownParamError(Exception):
    """The phase passes a param the actor does not declare."""

    def __init__(self, name: str) -> None:
        self.name = name
        super().__init__(f"unknown param '{name}'")


def resolve_params(
    actor: Actor, with_: Mapping[str, str], scope: Scope
) -> dict[str, str]:
    """The params the agent receives, as they are recorded in `phase_started`.

    Raises `UnresolvedError` for an expression without a value,
    `UnknownParamError` for a key the actor does not declare and
    `MissingParamError` for a required param nobody provides.
    """
    for name in with_:
        if name not in actor.params:
            raise UnknownParamError(name)
    values = {name: resolve_text(text, scope) for name, text in with_.items()}
    for name, param in actor.params.items():
        if name in values:
            continue
        if param.default is not None:
            values[name] = param.default
        elif param.required:
            raise MissingParamError(name)
    model = values.get("model")
    if model is not None and model in actor.models:
        values["model"] = actor.models[model]
    return values


def param_env(params: Mapping[str, str]) -> dict[str, str]:
    """`LASAGNA_PARAM_<NAME>` variables, upper case with `-` as `_`."""
    return {
        f"LASAGNA_PARAM_{name.upper().replace('-', '_')}": value
        for name, value in params.items()
    }
