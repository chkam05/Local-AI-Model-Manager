from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.models_menu_item import ModelsMenuItem


@dataclass(frozen=True, slots=True)
class ModelsMenuResultDto:
    dialog_result: DialogResultDto
    selected_item: ModelsMenuItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

