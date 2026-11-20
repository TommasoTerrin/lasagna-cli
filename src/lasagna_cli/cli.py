"""Command-line interface of Lasagna."""

from typing import Annotated

import typer

from lasagna_cli import __version__

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_USAGE = 2
EXIT_WAITING = 3
EXIT_INTERRUPTED = 130

app = typer.Typer(
    no_args_is_help=True,
    add_completion=False,
    help="Orchestrate pipelines whose phases are run by humans, machines or agents.",
)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"lasagna {__version__}")
        raise typer.Exit(EXIT_OK)


@app.callback()
def root(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Orchestrate pipelines whose phases are run by humans, machines or agents."""


def main() -> None:
    """Run the lasagna command."""
    app()
