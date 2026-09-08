from collections.abc import Iterable

from ai_models_manager.views.dialog import Dialog
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)
from ai_models_manager.views.models.dialog_button_model import (
    DialogButtonHandler,
    DialogButtonModel,
)


class DialogViewBuilder:
    """Build and render dialog widgets without exposing command arguments."""

    def __init__(self, dialog: Dialog) -> None:
        self._dialog = dialog
        self._title = ""
        self._content = ""
        self._help = ""
        self._height = "0"
        self._width = "0"
        self._menu_height = "0"
        self._default_item: str | None = None
        self._buttons: list[DialogButtonModel] = []
        self._items: list[tuple[str, str]] = []
        self._check_items: list[tuple[str, str, bool]] = []
        self._fields: list[tuple[str, str, int, int, int]] = []
        self._initial_value = ""
        self._widget = "menu"
        self._default_no = False
        self._separate_output = False
        self._scroll_text = False
        self._help_tags = False
        self._hide_tags = False
        self._hide_items = False
        self._wrap_content = False
        self._hot_list = True
        self._scrollbar = False
        self._theme = self._dialog.THEME_FILE

    def set_title(self, title: str) -> "DialogViewBuilder":
        self._title = title
        return self

    def set_content(self, content: str) -> "DialogViewBuilder":
        self._content = content
        return self

    def set_help(self, description: str) -> "DialogViewBuilder":
        self._help = description
        return self

    def set_height(self, height: str) -> "DialogViewBuilder":
        self._height = height
        return self

    def set_width(self, width: str) -> "DialogViewBuilder":
        self._width = width
        return self

    def set_menu_height(self, menu_height: str) -> "DialogViewBuilder":
        self._menu_height = menu_height
        return self

    def set_default_item(self, item_id: str | None) -> "DialogViewBuilder":
        self._default_item = item_id
        return self

    def set_theme(self, theme: object) -> "DialogViewBuilder":
        self._theme = theme
        return self

    def add_button(
        self,
        label: str,
        action: DialogButtonAction,
        handler: DialogButtonHandler | None = None,
        *,
        position: DialogButtonAction | None = None,
    ) -> "DialogViewBuilder":
        self._buttons.append(
            DialogButtonModel(label, action, position or action, handler)
        )
        return self

    def add_item(self, item_id: str, content: str) -> "DialogViewBuilder":
        self._items.append((item_id, content))
        return self

    def add_items(
        self, items: Iterable[tuple[str, str]]
    ) -> "DialogViewBuilder":
        for item_id, content in items:
            self.add_item(item_id, content)
        return self

    def add_check_item(
        self, item_id: str, content: str, selected: bool
    ) -> "DialogViewBuilder":
        self._check_items.append((item_id, content, selected))
        return self

    def add_field(
        self,
        label: str,
        value: str,
        row: int,
        input_column: int,
        length: int,
    ) -> "DialogViewBuilder":
        self._fields.append((label, value, row, input_column, length))
        return self

    def set_initial_value(self, value: str) -> "DialogViewBuilder":
        self._initial_value = value
        return self

    def use_default_no(self) -> "DialogViewBuilder":
        self._default_no = True
        return self

    def use_separate_output(self) -> "DialogViewBuilder":
        self._separate_output = True
        return self

    def use_scroll_text(self) -> "DialogViewBuilder":
        self._scroll_text = True
        return self

    def use_help_tags(self) -> "DialogViewBuilder":
        self._help_tags = True
        return self

    def hide_tags(self) -> "DialogViewBuilder":
        self._hide_tags = True
        return self

    def hide_items(self) -> "DialogViewBuilder":
        self._hide_items = True
        return self

    def wrap_content(self) -> "DialogViewBuilder":
        self._wrap_content = True
        return self

    def disable_hot_list(self) -> "DialogViewBuilder":
        self._hot_list = False
        return self

    def use_scrollbar(self) -> "DialogViewBuilder":
        self._scrollbar = True
        return self

    def show_menu(self) -> "DialogViewBuilder":
        self._widget = "menu"
        return self

    def show_form(self) -> "DialogViewBuilder":
        self._widget = "form"
        return self

    def show_checklist(self) -> "DialogViewBuilder":
        self._widget = "checklist"
        return self

    def show_input_box(self) -> "DialogViewBuilder":
        self._widget = "inputbox"
        return self

    def show_confirmation(self) -> "DialogViewBuilder":
        self._widget = "yesno"
        return self

    def show_message(self) -> "DialogViewBuilder":
        self._widget = "msgbox"
        return self

    def render(self) -> DialogResultDto:
        native_result = self._dialog.render_with_environment(
            self.build_arguments(),
            {self._dialog.ENV_DIALOGRC: str(self._theme)},
            capture_output=True,
        )
        result = self._semantic_result(native_result)
        self._handle_result(result)
        return result

    def build_arguments(self) -> list[str]:
        arguments = ["--title", self._title]
        for button in self._buttons:
            arguments.extend(self._button_arguments(button))
        if self._help_tags:
            arguments.append("--help-tags")
        if self._hide_tags:
            arguments.append("--no-tags")
        if self._hide_items:
            arguments.append("--no-items")
        if self._wrap_content:
            arguments.append("--cr-wrap")
        if not self._hot_list:
            arguments.append("--no-hot-list")
        if self._scrollbar:
            arguments.append("--scrollbar")
        if self._separate_output:
            arguments.append("--separate-output")
        if self._default_no:
            arguments.append("--defaultno")
        if self._scroll_text:
            arguments.append("--scrolltext")
        if self._help:
            arguments.extend(("--hline", self._help))
        if self._default_item is not None:
            arguments.extend(("--default-item", self._default_item))
        arguments.extend(self._widget_arguments())
        return arguments

    def _widget_arguments(self) -> list[str]:
        arguments = [f"--{self._widget}", self._content, self._height, self._width]
        if self._widget == "menu":
            arguments.append(self._menu_height)
            for item_id, content in self._items:
                arguments.extend((item_id, content))
        elif self._widget == "checklist":
            arguments.append(self._menu_height)
            for item_id, content, selected in self._check_items:
                arguments.extend((item_id, content, "on" if selected else "off"))
        elif self._widget == "form":
            arguments.append(str(len(self._fields)))
            for label, value, row, input_column, length in self._fields:
                arguments.extend(
                    (label, str(row), "1", value, str(row), str(input_column), str(length), "0")
                )
        elif self._widget == "inputbox":
            arguments.append(self._initial_value)
        return arguments

    @staticmethod
    def _button_arguments(button: DialogButtonModel) -> tuple[str, ...]:
        options = {
            DialogButtonAction.ACCEPT: ("--ok-label", button.label),
            DialogButtonAction.CANCEL: ("--cancel-label", button.label),
            DialogButtonAction.EXTRA: (
                "--extra-button",
                "--extra-label",
                button.label,
            ),
            DialogButtonAction.HELP: (
                "--help-button",
                "--help-label",
                button.label,
            ),
            DialogButtonAction.CONFIRM: ("--yes-label", button.label),
            DialogButtonAction.REJECT: ("--no-label", button.label),
        }
        return options[button.position]

    def _semantic_result(self, result: DialogResultDto) -> DialogResultDto:
        for button in self._buttons:
            if self._matches_result(button.position, result):
                return DialogResultDto(
                    self._exit_code(button.action),
                    result.output,
                )
        return result

    @staticmethod
    def _exit_code(action: DialogButtonAction) -> int:
        return {
            DialogButtonAction.ACCEPT: DialogResultDto.OK,
            DialogButtonAction.CONFIRM: DialogResultDto.OK,
            DialogButtonAction.CANCEL: DialogResultDto.CANCEL,
            DialogButtonAction.REJECT: DialogResultDto.CANCEL,
            DialogButtonAction.EXTRA: DialogResultDto.EXTRA,
            DialogButtonAction.HELP: DialogResultDto.HELP,
        }[action]

    def _handle_result(self, result: DialogResultDto) -> None:
        for button in self._buttons:
            if self._matches_result(button.action, result) and button.handler:
                button.handler(result)
                return

    @staticmethod
    def _matches_result(
        action: DialogButtonAction, result: DialogResultDto
    ) -> bool:
        return (
            result.accepted
            and action
            in {DialogButtonAction.ACCEPT, DialogButtonAction.CONFIRM}
        ) or (
            result.cancelled
            and action
            in {DialogButtonAction.CANCEL, DialogButtonAction.REJECT}
        ) or (
            result.requested_extra and action == DialogButtonAction.EXTRA
        ) or (
            result.requested_help and action == DialogButtonAction.HELP
        )
