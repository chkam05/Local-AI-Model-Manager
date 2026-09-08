from dataclasses import dataclass

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


@dataclass(frozen=True, slots=True)
class LocalModelsResultDto:
    dialog_result: DialogResultDto
    selected_model: LocalModel | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

    @property
    def sort_requested(self) -> bool:
        return self.dialog_result.requested_help

    @property
    def filter_requested(self) -> bool:
        return self.dialog_result.requested_extra
