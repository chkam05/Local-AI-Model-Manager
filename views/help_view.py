import re
import shutil
from typing import ClassVar

from ai_models_manager.views.dialog_colors import DialogColors
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)


class HelpView(DialogView[str, DialogResultDto]):
    TITLE: ClassVar[str] = "Help"
    WIDTH: ClassVar[str] = "0"
    MINIMUM_HEIGHT: ClassVar[int] = 10
    TERMINAL_VERTICAL_MARGIN: ClassVar[int] = 4

    def render(self, help_text: str) -> DialogResultDto:
        content = self._colorize(self._help_body(help_text))
        return (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(content)
            .add_button("Back", DialogButtonAction.ACCEPT)
            .set_height(self._dialog_height())
            .set_width(self.WIDTH)
            .use_scroll_text()
            .show_message()
            .render()
        )

    @classmethod
    def _dialog_height(cls) -> str:
        terminal_height = shutil.get_terminal_size().lines
        outside_margin = cls.TERMINAL_VERTICAL_MARGIN * 2
        return str(max(cls.MINIMUM_HEIGHT, terminal_height - outside_margin))

    @classmethod
    def _colorize(cls, text: str) -> str:
        lines: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.endswith(":") and not stripped.startswith("ai "):
                lines.append(DialogColors.heading(line))
                continue
            colored = re.sub(
                r"(?<![\w-])(--[a-z0-9-]+|-[a-zA-Z])(?![\w-])",
                lambda match: DialogColors.switch(match.group(0)),
                line,
            )
            colored = re.sub(
                r"(?<![\w])ai(?=\s|$)",
                lambda match: DialogColors.command(match.group(0)),
                colored,
            )
            colored = re.sub(
                r"\b(MODEL|SESSION|NAME|FILE|DIR|VALUE|FIELD|TARGET|"
                r"TOOL|COMPONENT|SOURCE|PROMPT|NEW_NAME|PX)\b",
                lambda match: DialogColors.value(match.group(0)),
                colored,
            )
            lines.append(colored)
        return "\n".join(lines)

    @staticmethod
    def _help_body(help_text: str) -> str:
        lines = help_text.splitlines()
        start = next(
            (
                index
                for index, line in enumerate(lines)
                if line.strip() == "USAGE:"
            ),
            0,
        )
        return "\n".join(lines[start:]).strip("\n")
