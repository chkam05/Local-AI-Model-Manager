from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.input_files_editor_dto import (
    InputFilesEditorDto,
)
from ai_models_manager.views.dtos.input_files_editor_result_dto import (
    InputFilesEditorResultDto,
)
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InputFilesEditorView(
    DialogView[InputFilesEditorDto, InputFilesEditorResultDto]
):
    TITLE: ClassVar[str] = "Input Files"

    def render(
        self, dto: InputFilesEditorDto
    ) -> InputFilesEditorResultDto:
        if not dto.paths:
            result = (
                self.build_view()
                .set_title(self.TITLE)
                .set_content("No input files have been selected.")
                .add_button("Add File", DialogButtonAction.CONFIRM)
                .add_button("Back", DialogButtonAction.REJECT)
                .show_confirmation()
                .render()
            )
            return InputFilesEditorResultDto(
                (
                    DialogResultDto(DialogResultDto.EXTRA)
                    if result.accepted
                    else result
                ),
                dto.paths,
            )
        view = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("Uncheck files to remove them from this command:")
            .add_button("Done", DialogButtonAction.ACCEPT)
            .add_button("Add File", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("14")
            .use_separate_output()
        )
        for index, path in enumerate(dto.paths):
            view.add_check_item(str(index), path, True)
        result = view.show_checklist().render()
        if result.accepted:
            selected = {
                int(value)
                for value in result.output.splitlines()
                if value.isdigit()
            }
            paths = tuple(
                path for index, path in enumerate(dto.paths) if index in selected
            )
        else:
            paths = dto.paths
        return InputFilesEditorResultDto(result, paths)
