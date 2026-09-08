from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.install_models_menu_dto import (
    InstallModelsMenuDto,
)
from ai_models_manager.views.dtos.install_models_menu_result_dto import (
    InstallModelsMenuResultDto,
)
from ai_models_manager.views.install_models_menu_item import (
    InstallModelsMenuItem,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class InstallModelsMenuView(
    DialogView[InstallModelsMenuDto, InstallModelsMenuResultDto]
):
    TITLE: ClassVar[str] = "Install Models"
    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "10"

    ITEMS: ClassVar[tuple[tuple[InstallModelsMenuItem, str], ...]] = (
        (
            InstallModelsMenuItem.DRAW_THINGS,
            "Browse the Draw Things model catalog",
        ),
        (
            InstallModelsMenuItem.OLLAMA,
            "Browse the Ollama Library",
        ),
        (
            InstallModelsMenuItem.OLLAMA_EXPERIMENTAL,
            "Browse experimental Ollama models",
        ),
        (
            InstallModelsMenuItem.FILE,
            "Install a model from a local file",
        ),
        (
            InstallModelsMenuItem.URL,
            "Download and install a model from a URL",
        ),
    )

    LABELS: ClassVar[dict[InstallModelsMenuItem, str]] = {
        InstallModelsMenuItem.DRAW_THINGS: "Draw Things Models",
        InstallModelsMenuItem.OLLAMA: "Ollama Models",
        InstallModelsMenuItem.OLLAMA_EXPERIMENTAL: (
            "Ollama Models Experimental"
        ),
        InstallModelsMenuItem.FILE: "Install from File",
        InstallModelsMenuItem.URL: "Install from URL",
    }

    def render(
        self, dto: InstallModelsMenuDto
    ) -> InstallModelsMenuResultDto:
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
        return InstallModelsMenuResultDto(result, selected_item)
