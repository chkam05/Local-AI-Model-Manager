from typing import ClassVar

from ai_models_manager.views.chat_option_item import ChatOptionItem
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.chat_options_dto import ChatOptionsDto
from ai_models_manager.views.dtos.chat_options_result_dto import (
    ChatOptionsResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ChatOptionsView(DialogView[ChatOptionsDto, ChatOptionsResultDto]):
    TITLE: ClassVar[str] = "Chat"
    HEIGHT: ClassVar[str] = "16"
    WIDTH: ClassVar[str] = "94"
    MENU_HEIGHT: ClassVar[str] = "7"
    LABEL_WIDTH: ClassVar[int] = 22

    def render(self, dto: ChatOptionsDto) -> ChatOptionsResultDto:
        items = (
            (ChatOptionItem.MODEL, "Model", dto.model or "Not selected"),
            (
                ChatOptionItem.CONTEXT_LENGTH,
                "Context Length",
                dto.context_length,
            ),
            (ChatOptionItem.SESSION, "Session", dto.session_name or "Ephemeral"),
            (
                ChatOptionItem.INPUT_FILES,
                "Input Files",
                self._input_files_summary(dto.input_files),
            ),
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("")
            .add_button("Edit", DialogButtonAction.ACCEPT)
            .add_button("Run", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_help("Up/Down Navigate   Enter Edit   Run Start Chat   Esc Back")
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .hide_tags()
            .disable_hot_list()
            .add_items(
                (
                    item.value,
                    f"{label:<{self.LABEL_WIDTH}} [{value}]",
                )
                for item, label, value in items
            )
            .show_menu()
            .render()
        )
        selected_item = next(
            (item for item, _, _ in items if result.output == item.value),
            None,
        )
        return ChatOptionsResultDto(result, dto, selected_item)

    @staticmethod
    def _input_files_summary(value: str) -> str:
        count = len([item for item in value.split(",") if item.strip()])
        if count == 0:
            return "None"
        return "1 selected" if count == 1 else f"{count} selected"
