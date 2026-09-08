from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.install_source_confirmation_dto import (
    InstallSourceConfirmationDto,
)
from ai_models_manager.views.dtos.install_confirmation_result_dto import (
    InstallConfirmationResultDto,
)
from ai_models_manager.views.install_source_option_view import (
    InstallSourceOptionView,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InstallSourceConfirmationView(
    DialogView[InstallSourceConfirmationDto, InstallConfirmationResultDto]
):
    TITLE: ClassVar[str] = "Confirm Installation"

    def render(
        self, dto: InstallSourceConfirmationDto
    ) -> InstallConfirmationResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(
                f"Source: {dto.source}\n\n"
                f"Type: {InstallSourceOptionView.LABELS[dto.option]}"
            )
            .add_button("Install", DialogButtonAction.CONFIRM)
            .add_button("Cancel", DialogButtonAction.REJECT)
            .use_default_no()
            .show_confirmation()
            .render()
        )
        return InstallConfirmationResultDto(result)
