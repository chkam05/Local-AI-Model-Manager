from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.models_menu_dto import ModelsMenuDto
from ai_models_manager.views.dtos.models_menu_result_dto import (
    ModelsMenuResultDto,
)
from ai_models_manager.views.models_menu_item import ModelsMenuItem
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ModelsMenuView(DialogView[ModelsMenuDto, ModelsMenuResultDto]):
    TITLE: ClassVar[str] = "Models Menu"
    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "9"

    ITEMS: ClassVar[tuple[tuple[ModelsMenuItem, str], ...]] = (
        (
            ModelsMenuItem.LOCAL,
            "Installed Ollama and Draw Things models",
        ),
        (
            ModelsMenuItem.DEPENDENCIES,
            "Draw Things dependencies and metadata",
        ),
        (
            ModelsMenuItem.INSTALL,
            "Browse model catalogs or install from source",
        ),
        (
            ModelsMenuItem.REFRESH,
            "Download the latest model catalog information",
        ),
    )

    LABELS: ClassVar[dict[ModelsMenuItem, str]] = {
        ModelsMenuItem.DEPENDENCIES: "Browse Dependencies",
        ModelsMenuItem.INSTALL: "Install Models",
        ModelsMenuItem.LOCAL: "Browse Local Models",
        ModelsMenuItem.REFRESH: "Refresh Models",
    }

    def render(self, dto: ModelsMenuDto) -> ModelsMenuResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("")
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .set_default_item(self.LABELS[dto.default_item] if dto.default_item else None)
            .add_items((self.LABELS[item], description) for item, description in self.ITEMS)
            .show_menu()
            .render()
        )
        selected_item = next(
            (
                item
                for item, label in self.LABELS.items()
                if result.accepted and label == result.output
            ),
            None,
        )
        return ModelsMenuResultDto(result, selected_item)
