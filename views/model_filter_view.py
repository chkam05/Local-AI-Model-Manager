from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.model_filter_dto import ModelFilterDto
from ai_models_manager.views.dtos.model_filter_result_dto import ModelFilterResultDto
from ai_models_manager.views.model_filter_item import ModelFilterItem
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ModelFilterView(DialogView[ModelFilterDto, ModelFilterResultDto]):
    TITLE: ClassVar[str] = "Model Filters"
    LABEL_WIDTH: ClassVar[int] = 16

    def render(self, dto: ModelFilterDto) -> ModelFilterResultDto:
        items = (
            (ModelFilterItem.NAME, "Name", dto.filters.name),
            (ModelFilterItem.BACKEND, "Backend", dto.filters.backend),
            (ModelFilterItem.TYPE, "Type", dto.filters.asset_type),
            (ModelFilterItem.STATE, "State", dto.filters.state),
            (ModelFilterItem.CATEGORY, "Category", dto.filters.category),
        )
        result = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content("Select a field to change. Filters are combined with AND.")
            .add_button("Edit", DialogButtonAction.ACCEPT)
            .add_button("Clear", DialogButtonAction.EXTRA)
            .add_button(
                "Apply",
                DialogButtonAction.HELP,
                position=DialogButtonAction.CANCEL,
            )
            .add_button(
                "Back",
                DialogButtonAction.CANCEL,
                position=DialogButtonAction.HELP,
            )
            .set_help("Enter Edit   Clear All   Apply Filters   Esc Back")
            .set_menu_height("8")
            .hide_tags()
            .disable_hot_list()
            .add_items(
                (
                    item.value,
                    f"{label:<{self.LABEL_WIDTH}} [{value or 'All'}]",
                )
                for item, label, value in items
            )
            .show_menu()
            .render()
        )
        selected = next(
            (item for item, _, _ in items if result.output == item.value),
            None,
        )
        return ModelFilterResultDto(result, selected)
