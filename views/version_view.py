import re
from typing import Callable, ClassVar, Sequence

from ai_models_manager.config import (
    APP_AUTHOR,
    APP_DESCRIPTION,
    APP_DISPLAY_NAME,
    APP_VERSION,
)
from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dialog_colors import DialogColors
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.version_dto import VersionDto
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class VersionView(DialogView[VersionDto, DialogResultDto]):
    TITLE: ClassVar[str] = "Version"
    CONTENT_WIDTH: ClassVar[int] = 96
    DIALOG_HEIGHT: ClassVar[str] = "32"
    DIALOG_WIDTH: ClassVar[str] = "100"
    SECTION_SEPARATOR: ClassVar[str] = "─" * CONTENT_WIDTH

    def render(self, dto: VersionDto) -> DialogResultDto:
        content = "\n".join(
            (
                f"Application name: {APP_DISPLAY_NAME}",
                f"Author:           {APP_AUTHOR}",
                f"Version:          {DialogColors.version(APP_VERSION)}",
                "",
                "Description:",
                APP_DESCRIPTION,
                "",
                self.SECTION_SEPARATOR,
                "",
                self._center_block(
                    self._table(
                        ("Component", "Version", "Size"),
                        tuple(
                            (row.component, row.version, row.size)
                            for row in dto.components
                        ),
                        (44, 26, 22),
                    ),
                ),
                "",
                self.SECTION_SEPARATOR,
                "",
                self._center_block(
                    self._table(
                        ("Model Storage", "Size"),
                        tuple(
                            (row.component, row.size)
                            for row in dto.model_storage
                        ),
                        (68, 26),
                    ),
                ),
            )
        )
        return (
            self.build_view()
            .set_title(self.TITLE)
            .set_content(content)
            .add_button("Back", DialogButtonAction.ACCEPT)
            .set_height(self.DIALOG_HEIGHT)
            .set_width(self.DIALOG_WIDTH)
            .use_scroll_text()
            .show_message()
            .render()
        )

    @classmethod
    def _table(
        cls,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
        minimum_widths: Sequence[int],
    ) -> str:
        widths = tuple(
            max(
                minimum_widths[index],
                len(headers[index]),
                *(len(row[index]) for row in rows),
            )
            for index in range(len(headers))
        )
        lines = [
            "  ".join(
                value.ljust(widths[index])
                for index, value in enumerate(headers)
            ).rstrip(),
            "  ".join("-" * width for width in widths),
        ]
        size_index = headers.index("Size") if "Size" in headers else None
        sizes = (
            tuple(DialogColors.size_bytes(row[size_index]) for row in rows)
            if size_index is not None
            else ()
        )
        positive_sizes = tuple(value for value in sizes if value > 0)
        minimum = min(positive_sizes, default=0)
        maximum = max(positive_sizes, default=0)
        for row in rows:
            cells: list[str] = []
            for index, value in enumerate(row):
                colorizer: Callable[[str], str] | None = None
                if headers[index] == "Version":
                    colorizer = DialogColors.version
                elif headers[index] == "Size":
                    size = DialogColors.size_bytes(value)
                    colorizer = lambda text, current=size: DialogColors.size_scale(
                        text, current, minimum, maximum
                    )
                colored = colorizer(value) if colorizer else value
                cells.append(colored + " " * (widths[index] - len(value)))
            lines.append("  ".join(cells).rstrip())
        return "\n".join(lines)

    @classmethod
    def _center_block(cls, value: str) -> str:
        lines = value.splitlines()
        block_width = max(
            (len(re.sub(r"\\Z.", "", line)) for line in lines),
            default=0,
        )
        padding = " " * max(0, (cls.CONTENT_WIDTH - block_width) // 2)
        return "\n".join(padding + line for line in lines)
