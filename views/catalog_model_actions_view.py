from typing import ClassVar

from ai_models_manager.views.catalog_model_action_item import CatalogModelActionItem
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.catalog_model_actions_dto import CatalogModelActionsDto
from ai_models_manager.views.dtos.catalog_model_actions_result_dto import (
    CatalogModelActionsResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class CatalogModelActionsView(
    DialogView[CatalogModelActionsDto, CatalogModelActionsResultDto]
):
    TITLE: ClassVar[str] = "Model Actions"

    def render(self, dto: CatalogModelActionsDto) -> CatalogModelActionsResultDto:
        items = (
            (CatalogModelActionItem.INSTALL, "Install"),
            (CatalogModelActionItem.DETAILS, "Details"),
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(f"Model: {dto.model.model.name}")
            .add_button("Select", DialogButtonAction.ACCEPT)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("6")
            .add_items((item.value, label) for item, label in items)
            .show_menu()
            .render()
        )
        selected = next(
            (item for item, _ in items if result.output == item.value),
            None,
        )
        return CatalogModelActionsResultDto(result, selected)
