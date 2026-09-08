from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InstallSourceDto:
    source: str = ""
    title: str = "Install from File"
