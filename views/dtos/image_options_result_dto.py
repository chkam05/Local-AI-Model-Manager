from dataclasses import dataclass

from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.image_options_dto import ImageOptionsDto
from ai_models_manager.views.image_option_item import ImageOptionItem


@dataclass(frozen=True, slots=True)
class ImageOptionsResultDto:
    dialog_result: DialogResultDto
    options: ImageOptionsDto | None = None
    selected_item: ImageOptionItem | None = None

    @property
    def cancelled(self) -> bool:
        return self.dialog_result.cancelled

    @property
    def input_files_requested(self) -> bool:
        return self.selected_item is ImageOptionItem.INPUT_FILES

    @property
    def run_requested(self) -> bool:
        return self.dialog_result.requested_extra
