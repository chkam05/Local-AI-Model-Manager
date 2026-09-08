from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.input_file_prompt_dto import (
    InputFilePromptDto,
)
from ai_models_manager.views.dtos.input_file_prompt_result_dto import (
    InputFilePromptResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InputFilePromptView(
    DialogView[InputFilePromptDto, InputFilePromptResultDto]
):
    TITLE: ClassVar[str] = "Add Input File"

    def render(self, dto: InputFilePromptDto) -> InputFilePromptResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("Enter a local file path:")
            .add_button("Add", DialogButtonAction.ACCEPT)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_height("0")
            .set_width("72")
            .set_initial_value(dto.path)
            .show_input_box()
            .render()
        )
        path = result.output.strip() if result.accepted else None
        return InputFilePromptResultDto(result, path or None)
