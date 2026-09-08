from pathlib import Path
from typing import ClassVar

from ai_models_manager.views.dialog_view import DialogView
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto
from ai_models_manager.views.dtos.directory_selection_dto import (
    DirectorySelectionDto,
)
from ai_models_manager.views.dtos.directory_selection_result_dto import (
    DirectorySelectionResultDto,
)
from ai_models_manager.views.models.dialog_button_action import DialogButtonAction


class DirectorySelectionView(
    DialogView[DirectorySelectionDto, DirectorySelectionResultDto]
):
    HEIGHT: ClassVar[str] = "22"
    WIDTH: ClassVar[str] = "100"
    MENU_HEIGHT: ClassVar[str] = "14"
    ITEM_WIDTH: ClassVar[int] = 88

    def render(self, dto: DirectorySelectionDto) -> DirectorySelectionResultDto:
        current = self._initial_directory(dto.directory)
        while True:
            entries = self._entries(current)
            result = self._render_directory(dto.title, current, entries)
            if result.cancelled:
                return DirectorySelectionResultDto(result)
            selected = entries.get(result.output)
            if selected is None:
                continue
            if result.accepted and result.output == "CURRENT":
                return DirectorySelectionResultDto(result, str(current))
            if result.requested_extra:
                return DirectorySelectionResultDto(result, str(selected))
            if selected.is_dir():
                current = selected.resolve()

    def _render_directory(
        self,
        title: str,
        current: Path,
        entries: dict[str, Path],
    ) -> DialogResultDto:
        view = (
            self.build_view()
            .set_title(title)
            .set_content(f"Directory: {current}")
            .add_button("Open", DialogButtonAction.ACCEPT)
            .add_button("Select", DialogButtonAction.EXTRA)
            .add_button("Back", DialogButtonAction.CANCEL)
            .set_help("Enter Open   Select Use highlighted directory   Esc Back")
            .set_height(self.HEIGHT)
            .set_width(self.WIDTH)
            .set_menu_height(self.MENU_HEIGHT)
            .hide_tags()
            .disable_hot_list()
            .use_scrollbar()
        )
        for entry_id, path in entries.items():
            if entry_id == "CURRENT":
                label = "[DIR]    ./"
            elif entry_id == "PARENT":
                label = "[DIR]    ../"
            else:
                label = f"[DIR]    {path.name}/"
            view.add_item(entry_id, label.ljust(self.ITEM_WIDTH))
        return view.show_menu().render()

    @staticmethod
    def _initial_directory(directory: str) -> Path:
        candidate = Path(directory).expanduser() if directory else Path.cwd()
        if candidate.is_dir():
            return candidate.resolve()
        return Path.home().resolve()

    @staticmethod
    def _entries(current: Path) -> dict[str, Path]:
        entries = {"CURRENT": current, "PARENT": current.parent}
        try:
            children = sorted(
                (path for path in current.iterdir() if path.is_dir()),
                key=lambda path: path.name.casefold(),
            )
        except OSError:
            children = []
        for index, path in enumerate(children, start=1):
            entries[f"D{index:06d}"] = path
        return entries
