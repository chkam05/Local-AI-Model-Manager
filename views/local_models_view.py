from typing import ClassVar

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.dialog_view_builder import DialogViewBuilder
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.local_models_dto import LocalModelsDto
from ai_models_manager.views.dtos.local_models_result_dto import (
    LocalModelsResultDto,
)
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)


class LocalModelsView(DialogView[LocalModelsDto, LocalModelsResultDto]):
    TITLE: ClassVar[str] = "Browse Local Models"
    OPTIONS_BUTTON_LABEL: ClassVar[str] = "Actions"
    FILTER_BUTTON_LABEL: ClassVar[str] = "Filter"
    SORT_BUTTON_LABEL: ClassVar[str] = "Sort"
    BACK_BUTTON_LABEL: ClassVar[str] = "Back"
    NAVIGATION_DESCRIPTION: ClassVar[str] = (
        "Up/Down Navigate   Enter Actions   F1 Filter   F2 Sort   Esc Back"
    )

    HEIGHT: ClassVar[str] = "0"
    WIDTH: ClassVar[str] = "0"
    MENU_HEIGHT: ClassVar[str] = "14"
    HEADER_INDENT: ClassVar[str] = "    "

    def render(self, dto: LocalModelsDto) -> LocalModelsResultDto:
        rows = self._rows(dto)
        result = self._build_view(dto, rows).render()
        selected_model = next(
            (
                model
                for row_id, model, _ in rows
                if (
                    result.accepted
                    or result.requested_extra
                    or result.requested_help
                )
                and row_id == result.output
            ),
            None,
        )
        return LocalModelsResultDto(result, selected_model)

    def _content(self, dto: LocalModelsDto) -> str:
        return self._header(dto.models)

    def _build_view(
        self,
        dto: LocalModelsDto,
        rows: tuple[tuple[str, LocalModel, str], ...],
    ) -> DialogViewBuilder:
        return (
            DialogViewBuilder(self.dialog)
            .set_title(self.TITLE)
            .set_content(self._content(dto))
            .add_button(
                self.OPTIONS_BUTTON_LABEL, DialogButtonAction.ACCEPT
            )
            .add_button(self.FILTER_BUTTON_LABEL, DialogButtonAction.EXTRA)
            .add_button(
                self.SORT_BUTTON_LABEL,
                DialogButtonAction.HELP,
                position=DialogButtonAction.CANCEL,
            )
            .add_button(
                self.BACK_BUTTON_LABEL,
                DialogButtonAction.CANCEL,
                position=DialogButtonAction.HELP,
            )
            .set_help(self.NAVIGATION_DESCRIPTION)
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .set_theme(self.dialog.MODEL_BROWSER_THEME_FILE)
            .use_help_tags()
            .hide_tags()
            .wrap_content()
            .set_default_item(self._default_item(dto, rows))
            .add_items((row_id, text) for row_id, _, text in rows)
        )

    def _default_item(
        self,
        dto: LocalModelsDto,
        rows: tuple[tuple[str, LocalModel, str], ...],
    ) -> str | None:
        return next(
            (
                row_id
                for row_id, model, _ in rows
                if self.model_key(model) == dto.default_model_key
            ),
            None,
        )

    @staticmethod
    def model_key(model: LocalModel) -> str:
        return f"{model.backend}\0{model.model.name}"

    def _rows(
        self, dto: LocalModelsDto
    ) -> tuple[tuple[str, LocalModel, str], ...]:
        widths = self._widths(dto.models)
        return tuple(
            (
                str(index),
                model,
                self._row(model, widths, dto.base_model),
            )
            for index, model in enumerate(dto.models)
        )

    def _header(self, models: tuple[LocalModel, ...]) -> str:
        widths = self._widths(models)
        labels = ("Model", "Backend", "Type", "State", "Size", "Rating", "Codex")
        return self.HEADER_INDENT + self._format_columns(labels, widths)

    def _row(
        self,
        model: LocalModel,
        widths: tuple[int, ...],
        base_model: str | None,
    ) -> str:
        name = model.model.name
        if model.backend == "Ollama" and base_model == name:
            name += " *"
        return self._format_columns(
            (
                name,
                model.backend,
                model.asset_type,
                model.state,
                self._size(model.model.size_bytes),
                model.rating,
                model.codex,
            ),
            widths,
        )

    def _widths(self, models: tuple[LocalModel, ...]) -> tuple[int, ...]:
        rows = [
            (
                model.model.name + " *",
                model.backend,
                model.asset_type,
                model.state,
                self._size(model.model.size_bytes),
                model.rating,
                model.codex,
            )
            for model in models
        ]
        labels = ("Model", "Backend", "Type", "State", "Size", "Rating", "Codex")
        return tuple(
            max(
                [len(labels[index]), *(len(row[index]) for row in rows)]
            )
            for index in range(len(labels))
        )

    @staticmethod
    def _format_columns(
        values: tuple[str, ...], widths: tuple[int, ...]
    ) -> str:
        return "  ".join(
            value.ljust(width) for value, width in zip(values, widths)
        ).rstrip()

    @staticmethod
    def _size(size_bytes: int) -> str:
        if size_bytes <= 0:
            return "-"
        return f"{size_bytes / 1024**3:.2f} GB"
