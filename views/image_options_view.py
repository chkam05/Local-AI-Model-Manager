from typing import ClassVar

from ai_models_manager.core.image_file_name import automatic_image_file_name
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.image_options_dto import ImageOptionsDto
from ai_models_manager.views.dtos.image_options_result_dto import (
    ImageOptionsResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction
from ai_models_manager.views.image_option_item import ImageOptionItem


class ImageOptionsView(DialogView[ImageOptionsDto, ImageOptionsResultDto]):
    TITLE: ClassVar[str] = "Image Generation"
    HEIGHT: ClassVar[str] = "19"
    WIDTH: ClassVar[str] = "94"
    MENU_HEIGHT: ClassVar[str] = "9"
    LABEL_WIDTH: ClassVar[int] = 22

    def render(self, dto: ImageOptionsDto) -> ImageOptionsResultDto:
        items = (
            (ImageOptionItem.MODEL, "Model", dto.model or "Not selected"),
            (ImageOptionItem.WIDTH, "Width", dto.width),
            (ImageOptionItem.HEIGHT, "Height", dto.height),
            (
                ImageOptionItem.DIRECTORY,
                "Target Directory",
                dto.output_directory or "Not selected",
            ),
            (
                ImageOptionItem.FILE_NAME,
                "File Name",
                dto.file_name or f"Automatic: {automatic_image_file_name(dto.model)}",
            ),
            (
                ImageOptionItem.INPUT_FILES,
                "Input Files",
                self._input_files_summary(dto.input_files),
            ),
            (ImageOptionItem.STRENGTH, "Strength", dto.strength or "0.35"),
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("")
            .add_button("Edit", DialogButtonAction.ACCEPT)
            .add_button("Run", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_help(
                "Up/Down Navigate   Enter Edit   Run Prompt/Generate   Esc Back"
            )
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
            (
                item
                for item, _, _ in items
                if result.output == item.value
            ),
            None,
        )
        return ImageOptionsResultDto(result, dto, selected_item)

    @staticmethod
    def _input_files_summary(value: str) -> str:
        count = len([item for item in value.split(",") if item.strip()])
        if count == 0:
            return "None"
        return "1 selected" if count == 1 else f"{count} selected"
