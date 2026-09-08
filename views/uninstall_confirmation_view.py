from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.uninstall_confirmation_dto import (
    UninstallConfirmationDto,
)
from ai_models_manager.views.dtos.uninstall_confirmation_result_dto import (
    UninstallConfirmationResultDto,
)
from ai_models_manager.views.uninstall_dependency_mode_item import (
    UninstallDependencyModeItem,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class UninstallConfirmationView(
    DialogView[UninstallConfirmationDto, UninstallConfirmationResultDto]
):
    TITLE: ClassVar[str] = "Confirm Uninstall"
    MODE_LABELS: ClassVar[dict[UninstallDependencyModeItem, str]] = {
        UninstallDependencyModeItem.ALL: "remove all dependencies",
        UninstallDependencyModeItem.KEEP: "keep dependencies",
        UninstallDependencyModeItem.UNUSED: "remove unused dependencies",
    }

    def render(
        self, dto: UninstallConfirmationDto
    ) -> UninstallConfirmationResultDto:
        message = f"Uninstall {dto.model.model.name}?"
        if (
            dto.model.backend == "Draw Things"
            and dto.model.asset_type == "Model"
        ):
            mode_label = self.MODE_LABELS[dto.dependency_mode]
            message += f"\n\nDependency mode: {mode_label}"
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(message)
            .add_button("Uninstall", DialogButtonAction.CONFIRM)
            .add_button("Cancel", DialogButtonAction.REJECT)
            .use_default_no()
            .show_confirmation()
            .render()
        )
        return UninstallConfirmationResultDto(result)
