from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComponentSelectionDto:
    title: str
    prompt: str
    components: tuple[tuple[str, str], ...]
    default_component: str = ""
