from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.install_source_option_item import (
    InstallSourceOptionItem,
)


@dataclass(frozen=True, slots=True)
class InstallSourceOptionResultDto:
    dialog_result: DialogResultDto
    selected_item: InstallSourceOptionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled
