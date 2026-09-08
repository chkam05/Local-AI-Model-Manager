from typing import ClassVar

from ai_models_manager.models.local_model import LocalModel
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.local_models_dto import LocalModelsDto
from ai_models_manager.views.dtos.local_models_result_dto import (
    LocalModelsResultDto,
)
from ai_models_manager.views.local_models_view import LocalModelsView
from ai_models_manager.views.dialog import Dialog
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class CatalogModelsView(DialogView[LocalModelsDto, LocalModelsResultDto]):
    TITLE: ClassVar[str] = "Browse Models"
    HEADER_INDENT: ClassVar[str] = "    "

    def __init__(self, dialog: Dialog, title: str) -> None:
        super().__init__(dialog)
        self.title = title

    def render(self, dto: LocalModelsDto) -> LocalModelsResultDto:
        widths = self._widths(dto.models)
        rows = tuple(
            (str(index), model, self._row(model, widths))
            for index, model in enumerate(dto.models)
        )
        default_id = next(
            (
                row_id
                for row_id, model, _ in rows
                if LocalModelsView.model_key(model) == dto.default_model_key
            ),
            None,
        )
        result = (
            self.build_view()
            .set_title(self.title)
            .set_content(self._header(dto.models, widths))
            .add_button("Actions", DialogButtonAction.ACCEPT)
            .add_button("Filter", DialogButtonAction.EXTRA)
            .add_button(
                "Sort",
                DialogButtonAction.HELP,
                position=DialogButtonAction.CANCEL,
            )
            .add_button(
                "Back",
                DialogButtonAction.CANCEL,
                position=DialogButtonAction.HELP,
            )
            .set_help(
                "Up/Down Navigate   Enter Actions   F1 Filter   F2 Sort   "
                "Esc Back   (Fn+F1/F2 on some Macs)"
            )
            .set_menu_height("14")
            .set_theme(self.dialog.MODEL_BROWSER_THEME_FILE)
            .use_help_tags()
            .hide_tags()
            .wrap_content()
            .set_default_item(default_id)
            .add_items((row_id, text) for row_id, _, text in rows)
            .show_menu()
            .render()
        )
        selected = next(
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
        return LocalModelsResultDto(result, selected)

    def _header(
        self, models: tuple[LocalModel, ...], widths: tuple[int, ...]
    ) -> str:
        return self.HEADER_INDENT + LocalModelsView._format_columns(
            self._labels(models),
            widths,
        )

    def _row(self, model: LocalModel, widths: tuple[int, ...]) -> str:
        name = model.model.name + (" *" if model.state == "Installed" else "")
        return LocalModelsView._format_columns(
            self._values(model, name),
            widths,
        )

    def _widths(self, models: tuple[LocalModel, ...]) -> tuple[int, ...]:
        labels = self._labels(models)
        rows = tuple(
            self._values(
                model,
                model.model.name
                + (" *" if model.state == "Installed" else ""),
            )
            for model in models
        )
        return tuple(
            max(len(labels[index]), *(len(row[index]) for row in rows))
            for index in range(len(labels))
        )

    def _labels(self, models: tuple[LocalModel, ...]) -> tuple[str, ...]:
        labels = ("Model", "Type", "Size", "Rating", "Codex", "Category")
        return labels + (("Filter",) if self._shows_filter(models) else ())

    def _values(self, model: LocalModel, name: str) -> tuple[str, ...]:
        values = (
            name,
            model.asset_type,
            LocalModelsView._size(model.model.size_bytes),
            model.rating,
            model.codex,
            model.category,
        )
        if model.backend == "Draw Things":
            return values + (model.content_filter,)
        return values

    @staticmethod
    def _shows_filter(models: tuple[LocalModel, ...]) -> bool:
        return any(model.backend == "Draw Things" for model in models)
