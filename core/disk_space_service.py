from pathlib import Path
import shutil
from typing import ClassVar
import urllib.error
import urllib.parse
import urllib.request

from ai_models_manager.core.models.disk_space_check import DiskSpaceCheck


class DiskSpaceService:
    """Check destination storage before copying or downloading known data."""

    MINIMUM_RESERVE_BYTES: ClassVar[int] = 512 * 1024**2
    RESERVE_RATIO: ClassVar[float] = 0.05
    HTTP_TIMEOUT_SECONDS: ClassVar[int] = 10

    def check(self, destination: Path, required_bytes: int) -> DiskSpaceCheck:
        target = self._existing_ancestor(destination.expanduser())
        reserve = max(
            self.MINIMUM_RESERVE_BYTES,
            int(max(required_bytes, 0) * self.RESERVE_RATIO),
        )
        return DiskSpaceCheck(
            available_bytes=shutil.disk_usage(target).free,
            destination=destination.expanduser(),
            required_bytes=max(required_bytes, 0),
            reserve_bytes=reserve,
        )

    def source_size(self, source: str) -> int:
        parsed = urllib.parse.urlparse(source)
        if parsed.scheme.casefold() not in {"http", "https"}:
            path = Path(source).expanduser()
            try:
                return path.stat().st_size if path.is_file() else 0
            except OSError:
                return 0
        request = urllib.request.Request(source, method="HEAD")
        try:
            with urllib.request.urlopen(
                request, timeout=self.HTTP_TIMEOUT_SECONDS
            ) as response:
                value = response.headers.get("Content-Length", "")
        except (urllib.error.URLError, OSError, ValueError):
            return 0
        try:
            return max(int(value), 0)
        except ValueError:
            return 0

    @staticmethod
    def format_size(value: int) -> str:
        if value >= 1024**3:
            return f"{value / 1024**3:.2f} GB"
        if value >= 1024**2:
            return f"{value / 1024**2:.1f} MB"
        if value >= 1024:
            return f"{value / 1024:.1f} KB"
        return f"{value} B"

    @staticmethod
    def _existing_ancestor(path: Path) -> Path:
        candidate = path
        while not candidate.exists() and candidate != candidate.parent:
            candidate = candidate.parent
        return candidate
