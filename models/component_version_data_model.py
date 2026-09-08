from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ComponentVersionDataModel:
    component: str
    version: str
    update: str
    size: str
