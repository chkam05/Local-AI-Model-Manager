from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.system_confirmation_dto import (
    SystemConfirmationDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class SystemConfirmationView(
    DialogView[SystemConfirmationDto, DialogResultDto]
):
    def render(self, dto: SystemConfirmationDto) -> DialogResultDto:
        return (
            self.build_view()
            .set_title(dto.title)
            .set_content(dto.message)
            .add_button(dto.confirm_label, DialogButtonAction.CONFIRM)
            .add_button("Cancel", DialogButtonAction.REJECT)
            .use_default_no()
            .show_confirmation()
            .render()
        )
