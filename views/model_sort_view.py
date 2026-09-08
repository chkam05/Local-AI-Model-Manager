from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.model_sort_dto import ModelSortDto
from ai_models_manager.views.dtos.model_sort_result_dto import (
    ModelSortResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class ModelSortView(DialogView[ModelSortDto, ModelSortResultDto]):
    TITLE: ClassVar[str] = "Sorting"
    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "10"
    HELP: ClassVar[str] = (
        "Up/Down Navigate   Enter Select/Place   ?/F2 Direction   "
        "Esc Back/Cancel"
    )
    FIELD_DESCRIPTIONS: ClassVar[dict[str, str]] = {
        "model": "Model / file name",
        "backend": "Ollama or Draw Things",
        "type": "Model, LoRA, Dependency, Metadata",
        "state": "Lifecycle state",
        "size": "Model / asset size",
        "rating": "Hardware Rating percentage",
        "codex": "Codex compatibility and coding quality",
        "filter": "Draw Things content-filter classification",
        "category": "Model category",
    }
    DEFAULT_DIRECTIONS: ClassVar[dict[str, str]] = {
        "state": "<",
        "rating": "<",
        "codex": "<",
    }

    def render(self, dto: ModelSortDto) -> ModelSortResultDto:
        fields = self._parse_order(dto.order)
        selected = fields[0][0]
        moving_field: str | None = None

        while True:
            result = self._render_menu(fields, selected, moving_field)
            if result.output:
                selected = result.output

            if result.accepted:
                if moving_field is None:
                    moving_field = selected
                else:
                    fields = self._move(fields, moving_field, selected)
                    selected = moving_field
                    moving_field = None
                continue
            if result.requested_extra:
                fields = self._toggle_direction(fields, selected)
                continue
            if result.cancelled and moving_field is not None:
                moving_field = None
                continue
            if result.cancelled:
                return ModelSortResultDto(
                    DialogResultDto(DialogResultDto.OK),
                    self._format_order(fields),
                )

    def _render_menu(
        self,
        fields: list[tuple[str, str]],
        selected: str,
        moving_field: str | None,
    ) -> DialogResultDto:
        header = f"  {'Column':<12}  {'Description':<42}  Direction"
        if moving_field is None:
            content = (
                "Top row has the highest sorting priority.\n"
                "Press Enter to select a column to move.\n\n"
                f"{header}"
            )
        else:
            content = (
                f"Moving: {moving_field}\n"
                "Use Up/Down to choose its new position, then press Enter "
                "to place it.\nPress Esc to cancel moving.\n\n"
                f"{header}"
            )

        view = (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(content)
            .add_button("Select", DialogButtonAction.ACCEPT)
            .add_button("Direction", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_help(self.HELP)
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .set_default_item(selected)
            .set_theme(self.dialog.MODEL_SORT_THEME_FILE)
            .hide_tags()
            .disable_hot_list()
        )
        for field, direction in fields:
            marker = ">" if field == moving_field else " "
            description = self.FIELD_DESCRIPTIONS[field]
            direction_label = "asc" if direction == ">" else "desc"
            view.add_item(
                field,
                f"{marker} {field:<12}  {description:<42}  [{direction_label}]",
            )
        return view.show_menu().render()

    @classmethod
    def _parse_order(cls, order: str) -> list[tuple[str, str]]:
        fields: list[tuple[str, str]] = []
        selected: set[str] = set()
        for raw_token in order.split(","):
            token = raw_token.strip()
            if not token:
                continue
            direction = token[-1] if token[-1:] in {"<", ">"} else ""
            field = token[:-1] if direction else token
            if field == "status":
                field = "state"
            if field not in cls.FIELD_DESCRIPTIONS or field in selected:
                continue
            fields.append(
                (field, direction or cls.DEFAULT_DIRECTIONS.get(field, ">"))
            )
            selected.add(field)
        for field in cls.FIELD_DESCRIPTIONS:
            if field not in selected:
                fields.append(
                    (field, cls.DEFAULT_DIRECTIONS.get(field, ">"))
                )
        return fields

    @staticmethod
    def _toggle_direction(
        fields: list[tuple[str, str]], selected: str
    ) -> list[tuple[str, str]]:
        return [
            (field, "<" if direction == ">" else ">")
            if field == selected
            else (field, direction)
            for field, direction in fields
        ]

    @staticmethod
    def _move(
        fields: list[tuple[str, str]], moving: str, target: str
    ) -> list[tuple[str, str]]:
        moving_item = next(item for item in fields if item[0] == moving)
        remaining = [item for item in fields if item[0] != moving]
        target_index = next(
            (
                index
                for index, item in enumerate(fields)
                if item[0] == target
            ),
            0,
        )
        remaining.insert(min(target_index, len(remaining)), moving_item)
        return remaining

    @staticmethod
    def _format_order(fields: list[tuple[str, str]]) -> str:
        return ",".join(f"{field}{direction}" for field, direction in fields)
