from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class InputFilePromptDto:
    path: str = ""
