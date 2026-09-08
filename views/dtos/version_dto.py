from dataclasses import dataclass

from ai_models_manager.models.component_version_data_model import (
    ComponentVersionDataModel,
)
from ai_models_manager.models.model_storage_data_model import (
    ModelStorageDataModel,
)


@dataclass(frozen=True, slots=True)
class VersionDto:
    components: tuple[ComponentVersionDataModel, ...]
    model_storage: tuple[ModelStorageDataModel, ...]
