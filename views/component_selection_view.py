from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.component_selection_dto import (
    ComponentSelectionDto,
)
from ai_models_manager.views.dtos.component_selection_result_dto import (
    ComponentSelectionResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ComponentSelectionView(
    DialogView[ComponentSelectionDto, ComponentSelectionResultDto]
):
    def render(
        self, dto: ComponentSelectionDto
    ) -> ComponentSelectionResultDto:
        result = (
            self.build_view()
            .set_title(dto.title)
            .set_content(dto.prompt)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("12")
            .set_default_item(dto.default_component or None)
            .add_items(dto.components)
            .show_menu()
            .render()
        )
        return ComponentSelectionResultDto(
            result,
            result.output if result.accepted else None,
        )
