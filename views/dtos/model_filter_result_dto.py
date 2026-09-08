from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.model_filter_item import ModelFilterItem


@dataclass(frozen=True, slots=True)
class ModelFilterResultDto:
    dialog_result: DialogResultDto
    selected_item: ModelFilterItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

    @property
    def clear_requested(self) -> bool:
        return self.dialog_result.requested_extra

    @property
    def apply_requested(self) -> bool:
        return self.dialog_result.requested_help
