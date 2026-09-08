from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.system_menu_item import SystemMenuItem


@dataclass(frozen=True, slots=True)
class SystemMenuResultDto:
    dialog_result: DialogResultDto
    selected_item: SystemMenuItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled
