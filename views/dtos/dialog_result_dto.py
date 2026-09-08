from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class DialogResultDto:
    """Exit status and optional value returned by a dialog widget."""

    OK: ClassVar[int] = 0
    CANCEL: ClassVar[int] = 1
    HELP: ClassVar[int] = 2
    EXTRA: ClassVar[int] = 3
    ITEM_HELP: ClassVar[int] = 4
    ESCAPE: ClassVar[int] = 255

    exit_code: int
    output: str = ""

    @property
    def accepted(self) -> bool:
        return self.exit_code == self.OK

    @property
    def cancelled(self) -> bool:
        return self.exit_code in {self.CANCEL, self.ESCAPE}

    @property
    def requested_extra(self) -> bool:
        return self.exit_code == self.EXTRA

    @property
    def requested_help(self) -> bool:
        return self.exit_code in {self.HELP, self.ITEM_HELP}

