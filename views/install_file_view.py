from pathlib import Path
from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.install_source_dto import InstallSourceDto
from ai_models_manager.views.dtos.install_source_result_dto import (
    InstallSourceResultDto,
)
from ai_models_manager.views.models.dialog_button_action import (
    DialogButtonAction,
)


class InstallFileView(DialogView[InstallSourceDto, InstallSourceResultDto]):
    TITLE: ClassVar[str] = "Install from File"
    HEIGHT: ClassVar[str] = "22"
    WIDTH: ClassVar[str] = "100"
    MENU_HEIGHT: ClassVar[str] = "14"
    ITEM_WIDTH: ClassVar[int] = 88

    def render(self, dto: InstallSourceDto) -> InstallSourceResultDto:
        current = self._initial_directory(dto.source)
        while True:
            entries = self._entries(current)
            result = self._render_directory(dto.title, current, entries)
            if result.cancelled:
                return InstallSourceResultDto(result)
            selected = entries.get(result.output)
            if selected is None:
                continue
            if selected.is_dir():
                if result.accepted:
                    current = selected
                    continue
                self._show_directory_message(dto.title)
                continue
            if selected.is_file():
                return InstallSourceResultDto(result, str(selected))

    def _render_directory(
        self, title: str, current: Path, entries: dict[str, Path]
    ) -> DialogResultDto:
        view = (
            self.build_view()
            .set_title(title)
            .set_content(f"Directory: {current}")
            .add_button("Open", DialogButtonAction.ACCEPT)
            .add_button("Select", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_help("Enter: open folder / select file")
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .hide_tags()
            .disable_hot_list()
            .use_scrollbar()
        )
        for entry_id, path in entries.items():
            label = self._entry_label(entry_id, path)
            view.add_item(entry_id, label.ljust(self.ITEM_WIDTH))
        return view.show_menu().render()

    @staticmethod
    def _entry_label(entry_id: str, path: Path) -> str:
        if entry_id == "PARENT":
            return "[DIR]  .."
        if path.is_dir():
            return f"[DIR]  {path.name}/"
        return f"[FILE] {path.name}"

    def _show_directory_message(self, title: str) -> None:
        (
            self.build_view()
            .set_title(title)
            .set_content(
                "Select is only for files. Use Open or press Enter to "
                "enter the highlighted directory."
            )
            .add_button("Back", DialogButtonAction.ACCEPT)
            .show_message()
            .render()
        )

    @staticmethod
    def _initial_directory(source: str) -> Path:
        candidate = Path(source).expanduser() if source else Path.home()
        if candidate.is_file():
            return candidate.parent.resolve()
        if candidate.is_dir():
            return candidate.resolve()
        return Path.home().resolve()

    @staticmethod
    def _entries(current: Path) -> dict[str, Path]:
        entries = {"PARENT": current.parent}
        try:
            children = sorted(
                current.iterdir(),
                key=lambda path: (not path.is_dir(), path.name.casefold()),
            )
        except OSError:
            children = []
        directory_index = 0
        file_index = 0
        for path in children:
            if path.is_dir():
                directory_index += 1
                entry_id = f"D{directory_index:06d}"
            else:
                file_index += 1
                entry_id = f"F{file_index:06d}"
            entries[entry_id] = path
        return entries
