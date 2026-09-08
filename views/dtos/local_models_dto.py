from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel


@dataclass(frozen=True, slots=True)
class LocalModelsDto:
    models: tuple[LocalModel, ...]
    base_model: str | None = None
    default_model_key: str | None = None

