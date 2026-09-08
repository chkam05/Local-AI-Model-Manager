from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComponentChecklistDto:
    title: str
    headers: tuple[str, ...]
    components: tuple[tuple[str, tuple[str, ...], bool], ...]
