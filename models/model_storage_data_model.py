from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ModelStorageDataModel:
    component: str
    size: str
