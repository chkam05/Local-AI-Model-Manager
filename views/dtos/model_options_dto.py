from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.model_option_item import ModelOptionItem


@dataclass(frozen=True, slots=True)
class ModelOptionsDto:
    model: LocalModel
    default_item: ModelOptionItem | None = None

