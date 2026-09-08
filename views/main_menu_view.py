from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.main_menu_dto import MainMenuDto
from ai_models_manager.views.dtos.main_menu_result_dto import MainMenuResultDto
from ai_models_manager.views.main_menu_item import MainMenuItem
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class MainMenuView(DialogView[MainMenuDto, MainMenuResultDto]):
    TITLE: ClassVar[str] = "Main Menu"
    PROMPT: ClassVar[str] = ""
    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "12"

    ITEMS: ClassVar[tuple[tuple[MainMenuItem, str], ...]] = (
        (MainMenuItem.AGENT, "Agent"),
        (MainMenuItem.CHAT, "Chat"),
        (MainMenuItem.IMAGE, "Image Generation"),
        (MainMenuItem.MODELS, "Models"),
        (MainMenuItem.HELP, "Help"),
        (MainMenuItem.SYSTEM, "System"),
        (MainMenuItem.VERSION, "Version"),
        (MainMenuItem.EXIT, "Exit"),
    )

    def render(self, dto: MainMenuDto) -> MainMenuResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(self.PROMPT)
            .add_button("Exit", DialogButtonAction.CANCEL)
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .hide_tags()
            .set_default_item(dto.default_item.value if dto.default_item else None)
            .add_items((item.value, description) for item, description in self.ITEMS)
            .show_menu()
            .render()
        )
        try:
            selected_item = (
                MainMenuItem(result.output) if result.accepted else None
            )
        except ValueError:
            selected_item = None
        return MainMenuResultDto(result, selected_item)
