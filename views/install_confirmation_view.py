from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.install_confirmation_dto import (
    InstallConfirmationDto,
)
from ai_models_manager.views.dtos.install_confirmation_result_dto import (
    InstallConfirmationResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InstallConfirmationView(
    DialogView[InstallConfirmationDto, InstallConfirmationResultDto]
):
    TITLE: ClassVar[str] = "Confirm Installation"

    def render(
        self, dto: InstallConfirmationDto
    ) -> InstallConfirmationResultDto:
        installed_note = (
            "\n\nThis model is already installed. Installation will check "
            "for updates."
            if dto.model.state == "Installed"
            else ""
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(f"Install {dto.model.model.name}?{installed_note}")
            .add_button("Install", DialogButtonAction.CONFIRM)
            .add_button("Cancel", DialogButtonAction.REJECT)
            .use_default_no()
            .show_confirmation()
            .render()
        )
        return InstallConfirmationResultDto(result)
