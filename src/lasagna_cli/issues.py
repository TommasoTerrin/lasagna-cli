"""Problems found while checking a project."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Issue:
    """One validation finding.

    `file` is a POSIX path relative to the repo root; `field` is a dotted path
    such as `phases[1].with.command`, or empty for the whole file.
    """

    file: str
    field: str
    message: str
    severity: Literal["error", "warning"] = "error"

    def __str__(self) -> str:
        where = f"{self.file}: {self.field}: " if self.field else f"{self.file}: "
        return f"{self.severity}: {where}{self.message}"
