from dataclasses import dataclass

from ai_models_manager.views.models.model_filters import ModelFilters


@dataclass(frozen=True, slots=True)
class ModelFilterDto:
    filters: ModelFilters
