from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelDetailsDataModel:
    update: str = "-"
    path: str = "-"
    tools: str = "N/A"
    vision: str = "N/A"
    image_generation: str = "N/A"
    dependencies: tuple[str, ...] = ()
    dependency_users: tuple[str, ...] = ()
