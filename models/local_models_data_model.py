from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel


@dataclass(frozen=True, slots=True)
class LocalModelsDataModel:
    models: tuple[LocalModel, ...]
    warning: str | None = None

