import json
from pathlib import Path
import tempfile
import threading
from typing import ClassVar

from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.models.tool_settings_data_model import ToolSettingsDataModel


class ToolSettingsStorage:
    """Thread-safe, atomic JSON storage for Codex tool switches."""

    ENCODING: ClassVar[str] = "utf-8"
    FILE_NAME: ClassVar[str] = "tools.json"
    INDENT: ClassVar[int] = 4

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or SettingsStorage._default_directory()
        self.file_path = self.directory / self.FILE_NAME
        self._lock = threading.RLock()

    def load(self) -> ToolSettingsDataModel:
        with self._lock:
            try:
                with self.file_path.open("r", encoding=self.ENCODING) as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                return ToolSettingsDataModel()
            if not isinstance(data, dict):
                return ToolSettingsDataModel()
            return ToolSettingsDataModel.from_dict(data)

    def save(self, model: ToolSettingsDataModel) -> None:
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True)
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    "w",
                    delete=False,
                    dir=self.directory,
                    encoding=self.ENCODING,
                ) as file:
                    temporary_path = Path(file.name)
                    json.dump(
                        model.to_dict(),
                        file,
                        ensure_ascii=False,
                        indent=self.INDENT,
                    )
                    file.write("\n")
                temporary_path.chmod(0o600)
                temporary_path.replace(self.file_path)
            finally:
                if temporary_path is not None and temporary_path.exists():
                    temporary_path.unlink()
