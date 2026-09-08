from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.system_menu_dto import SystemMenuDto
from ai_models_manager.views.dtos.system_menu_result_dto import SystemMenuResultDto
from ai_models_manager.views.system_menu_item import SystemMenuItem
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class SystemMenuView(DialogView[SystemMenuDto, SystemMenuResultDto]):
    TITLE: ClassVar[str] = "System"
    ITEMS: ClassVar[tuple[tuple[SystemMenuItem, str], ...]] = (
        (SystemMenuItem.SETUP, "Install missing application components"),
        (SystemMenuItem.UPDATE, "Update all or one component"),
        (SystemMenuItem.PURGE, "Remove components or model data"),
        (SystemMenuItem.TOOLS, "Configure tools available to agents"),
    )

    def render(self, dto: SystemMenuDto) -> SystemMenuResultDto:
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("")
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("8")
            .set_default_item(dto.default_item.value if dto.default_item else None)
            .add_items((item.value, description) for item, description in self.ITEMS)
            .show_menu()
            .render()
        )
        try:
            selected = SystemMenuItem(result.output) if result.accepted else None
        except ValueError:
            selected = None
        return SystemMenuResultDto(result, selected)
