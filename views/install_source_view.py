from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.install_source_dto import InstallSourceDto
from ai_models_manager.views.dtos.install_source_result_dto import (
    InstallSourceResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InstallSourceView(DialogView[InstallSourceDto, InstallSourceResultDto]):
    TITLE: ClassVar[str] = "Install from URL"

    def render(self, dto: InstallSourceDto) -> InstallSourceResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("Enter a model URL:")
            .add_button("Next", DialogButtonAction.ACCEPT)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_height("0")
            .set_width("72")
            .set_initial_value(dto.source)
            .show_input_box()
            .render()
        )
        source = result.output.strip() if result.accepted else None
        return InstallSourceResultDto(result, source or None)
