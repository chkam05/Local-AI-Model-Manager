from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.component_checklist_dto import (
    ComponentChecklistDto,
)
from ai_models_manager.views.dtos.component_checklist_result_dto import (
    ComponentChecklistResultDto,
)
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)


class ComponentChecklistView(
    DialogView[ComponentChecklistDto, ComponentChecklistResultDto]
):
    CHECKLIST_PREFIX_WIDTH = 6

    def render(
        self, dto: ComponentChecklistDto
    ) -> ComponentChecklistResultDto:
        widths = self._widths(dto)
        header = self._format_row(dto.headers, widths)
        content = " " * self.CHECKLIST_PREFIX_WIDTH + header
        view = (
            self.build_view()
            .set_title(dto.title)
            .set_content(content)
            .add_button("Apply", DialogButtonAction.ACCEPT)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_menu_height("12")
            .use_separate_output()
            .hide_tags()
            .disable_hot_list()
        )
        component_ids: dict[str, str] = {}
        for index, (value, cells, selected) in enumerate(dto.components):
            item_id = str(index)
            component_ids[item_id] = value
            view.add_check_item(
                item_id,
                self._format_row(cells, widths),
                selected,
            )
        result = view.show_checklist().render()
        components = (
            frozenset(
                component_ids[item_id]
                for item_id in result.output.splitlines()
                if item_id in component_ids
            )
            if result.accepted
            else frozenset()
        )
        return ComponentChecklistResultDto(result, components)

    @staticmethod
    def _widths(dto: ComponentChecklistDto) -> tuple[int, ...]:
        return tuple(
            max(
                len(header),
                *(len(cells[index]) for _, cells, _ in dto.components),
            )
            for index, header in enumerate(dto.headers)
        )

    @staticmethod
    def _format_row(values: tuple[str, ...], widths: tuple[int, ...]) -> str:
        return "  ".join(
            value.ljust(width) for value, width in zip(values, widths)
        ).rstrip()
