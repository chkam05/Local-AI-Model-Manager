from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.main_menu_item import MainMenuItem


@dataclass(frozen=True, slots=True)
class MainMenuResultDto:
    dialog_result: DialogResultDto
    selected_item: MainMenuItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

