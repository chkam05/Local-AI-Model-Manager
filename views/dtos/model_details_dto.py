from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.models.model_details_data_model import (
    ModelDetailsDataModel,
)


@dataclass(frozen=True, slots=True)
class ModelDetailsDto:
    model: LocalModel
    base_model: str | None = None
    details: ModelDetailsDataModel = ModelDetailsDataModel()
