from dataclasses import dataclass

from ai_models_manager.views.dtos.chat_options_dto import ChatOptionsDto
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.chat_option_item import ChatOptionItem


@dataclass(frozen=True, slots=True)
class ChatOptionsResultDto:
    dialog_result: DialogResultDto
    options: ChatOptionsDto | None = None
    selected_item: ChatOptionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

    @property
    def run_requested(self) -> bool:
        return self.dialog_result.requested_extra

    @property
    def input_files_requested(self) -> bool:
        return self.selected_item is ChatOptionItem.INPUT_FILES
