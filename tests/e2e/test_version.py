from typer.testing import CliRunner

import lasagna
from lasagna.cli import app


# AC-V3-002
def test_version_flag_prints_package_and_protocol_versions_and_exits_zero():
    result = CliRunner().invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"lasagna {lasagna.__version__} (protocol {lasagna.PROTOCOL_VERSION})\n"
    assert lasagna.PROTOCOL_VERSION == "3.0"
