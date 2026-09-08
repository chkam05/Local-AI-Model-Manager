import json
import os
from pathlib import Path
import tempfile
import threading
from typing import ClassVar

from ai_models_manager.config import APP_NAME
from ai_models_manager.models.settings_data_model import SettingsDataModel


class SettingsStorage:
    """Thread-safe JSON storage for application settings."""

    ENCODING: ClassVar[str] = "utf-8"
    FILE_NAME: ClassVar[str] = "settings.json"
    INDENT: ClassVar[int] = 4

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or self._default_directory()
        self.file_path = self.directory / self.FILE_NAME
        self._lock = threading.RLock()

    @staticmethod
    def _default_directory() -> Path:
        config_home = os.environ.get("XDG_CONFIG_HOME")
        root = Path(config_home).expanduser() if config_home else Path.home() / ".config"
        return root / APP_NAME

    def load(self) -> SettingsDataModel:
        """Load settings or return defaults for a missing or invalid file."""
        with self._lock:
            try:
                with self.file_path.open("r", encoding=self.ENCODING) as file:
                    data = json.load(file)
            except (FileNotFoundError, json.JSONDecodeError, OSError):
                return SettingsDataModel.from_dict({})

            if not isinstance(data, dict):
                return SettingsDataModel.from_dict({})

            return SettingsDataModel.from_dict(data)

    def save(self, model: SettingsDataModel) -> None:
        """Save settings atomically as formatted JSON."""
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
