from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.model_option_item import ModelOptionItem


@dataclass(frozen=True, slots=True)
class ModelOptionsResultDto:
    dialog_result: DialogResultDto
    selected_item: ModelOptionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

