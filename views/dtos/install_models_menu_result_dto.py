from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.install_models_menu_item import (
    InstallModelsMenuItem,
)


@dataclass(frozen=True, slots=True)
class InstallModelsMenuResultDto:
    dialog_result: DialogResultDto
    selected_item: InstallModelsMenuItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

