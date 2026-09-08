from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DirectorySelectionDto:
    directory: str = ""
    title: str = "Select Directory"
