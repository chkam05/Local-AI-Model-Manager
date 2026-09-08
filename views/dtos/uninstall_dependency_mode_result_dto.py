from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.uninstall_dependency_mode_item import (
    UninstallDependencyModeItem,
)


@dataclass(frozen=True, slots=True)
class UninstallDependencyModeResultDto:
    dialog_result: DialogResultDto
    selected_item: UninstallDependencyModeItem | None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled
