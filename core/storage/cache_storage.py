import os
from pathlib import Path
from typing import ClassVar

from ai_models_manager.core.destructive_path_validator import (
    DestructivePathValidator,
)


class CacheStorage:
    """Storage location for disposable application cache files."""

    ENV_CACHE_HOME: ClassVar[str] = "XDG_CACHE_HOME"
    DIRECTORY_NAME: ClassVar[str] = "ai"

    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or self._default_directory()

    @classmethod
    def _default_directory(cls) -> Path:
        cache_home = os.environ.get(cls.ENV_CACHE_HOME)
        root = (
            Path(cache_home).expanduser()
            if cache_home
            else Path.home() / ".cache"
        )
        return root / cls.DIRECTORY_NAME

    def clear(self) -> int:
        """Remove cache contents and return the number of removed files."""
        directory = DestructivePathValidator.directory(
            self.directory, "cache directory"
        )
        if not directory.is_dir():
            return 0

        removed_files = 0
        for root, directories, files in os.walk(
            directory,
            topdown=False,
            followlinks=False,
        ):
            root_path = Path(root)
            for file_name in files:
                (root_path / file_name).unlink()
                removed_files += 1
            for directory_name in directories:
                path = root_path / directory_name
                if path.is_symlink():
                    path.unlink()
                    removed_files += 1
                else:
                    path.rmdir()
        return removed_files
