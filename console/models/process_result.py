from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ProcessResult:
    """Result of an external process execution."""

    command: tuple[str, ...]
    return_code: int
    stdout: str = ""
    stderr: str = ""

    @property
    def succeeded(self) -> bool:
        return self.return_code == 0

    @property
    def failed(self) -> bool:
        return not self.succeeded
