from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import re
import shutil
from typing import ClassVar, Sequence

from ai_models_manager.config import APP_VERSION
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.models.component_version_data_model import ComponentVersionDataModel
from ai_models_manager.models.model_storage_data_model import ModelStorageDataModel


class VersionService:
    """Collect installed versions, available updates and disk usage."""

    CODEX_PACKAGE: ClassVar[str] = "@openai/codex"
    ENV_OLLAMA_MODELS: ClassVar[str] = "OLLAMA_MODELS"
    GITHUB_API_OLLAMA: ClassVar[str] = (
        "https://api.github.com/repos/ollama/ollama/releases/latest"
    )
    NOT_INSTALLED: ClassVar[str] = "Not installed"
    NO_UPDATE: ClassVar[str] = "-"
    UPDATE_TIMEOUT_SECONDS: ClassVar[int] = 8
    VERSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<!\d)(\d+(?:\.\d+)+(?:[-+][0-9A-Za-z.-]+)?)"
    )

    def __init__(
        self,
        process_runner: ProcessRunner,
        draw_things: DrawThingsBackend,
    ) -> None:
        self.process_runner = process_runner
        self.draw_things = draw_things

    def components(self) -> tuple[ComponentVersionDataModel, ...]:
        collectors = (
            self._ai_component,
            self._codex_component,
            self._dialog_component,
            self._draw_things_component,
            self._imagemagick_component,
            self._npm_component,
            self._ollama_component,
        )
        with ThreadPoolExecutor(max_workers=len(collectors)) as executor:
            rows = tuple(executor.map(lambda collector: collector(), collectors))
        return tuple(sorted(rows, key=lambda row: row.component.casefold()))

    def model_storage(self) -> tuple[ModelStorageDataModel, ...]:
        ollama_directory = Path(
            os.environ.get(
                self.ENV_OLLAMA_MODELS,
                str(Path.home() / ".ollama" / "models"),
            )
        ).expanduser()
        ollama_bytes = self._disk_bytes(ollama_directory)
        draw_things_bytes = self._disk_bytes(self.draw_things.models_directory)
        return (
            ModelStorageDataModel(
                "Ollama models", self.format_bytes(ollama_bytes)
            ),
            ModelStorageDataModel(
                "Draw Things models + assets",
                self.format_bytes(draw_things_bytes),
            ),
            ModelStorageDataModel(
                "Total models storage",
                self.format_bytes(ollama_bytes + draw_things_bytes),
            ),
        )

    def _ai_component(self) -> ComponentVersionDataModel:
        package_directory = Path(__file__).resolve().parents[1]
        return self._row(
            "AI Model Manager",
            APP_VERSION,
            None,
            package_directory,
        )

    def _codex_component(self) -> ComponentVersionDataModel:
        executable = shutil.which("codex")
        version = self._command_version([executable, "--version"]) if executable else None
        latest = self._npm_latest(self.CODEX_PACKAGE) if version else None
        path = self._npm_package_path(self.CODEX_PACKAGE) or self._path(executable)
        return self._row("Codex CLI", version, latest, path)

    def _dialog_component(self) -> ComponentVersionDataModel:
        executable = shutil.which("dialog")
        version = self._command_version([executable, "--version"]) if executable else None
        latest = self._brew_latest("dialog") if version else None
        path = self._brew_prefix("dialog") or self._path(executable)
        return self._row("dialog", version, latest, path)

    def _draw_things_component(self) -> ComponentVersionDataModel:
        executable = shutil.which(self.draw_things.EXECUTABLE)
        version = self._brew_installed_version("draw-things-cli")
        if version is None and executable:
            version = self._command_version([executable, "--version"])
        latest = self._brew_latest("draw-things-cli") if version else None
        path = self._brew_prefix("draw-things-cli") or self._path(executable)
        return self._row("Draw Things CLI", version, latest, path)

    def _npm_component(self) -> ComponentVersionDataModel:
        executable = shutil.which("npm")
        version = self._command_version([executable, "--version"]) if executable else None
        latest = self._npm_latest("npm") if version else None
        path = self._npm_package_path("npm") or self._path(executable)
        return self._row("npm", version, latest, path)

    def _imagemagick_component(self) -> ComponentVersionDataModel:
        executable = shutil.which("magick") or shutil.which("montage")
        version = self._brew_installed_version("imagemagick")
        if version is None and executable:
            version = self._imagemagick_version(executable)
        latest = self._brew_latest("imagemagick") if version else None
        path = self._brew_prefix("imagemagick") or self._path(executable)
        return self._row("ImageMagick", version, latest, path)

    def _imagemagick_version(self, executable: str) -> str | None:
        result = self.process_runner.run(
            [executable, "--version"],
            capture_output=True,
            timeout=self.UPDATE_TIMEOUT_SECONDS,
        )
        if result.failed:
            return None
        return self._normalize_version(
            "\n".join((result.stdout, result.stderr))
        )

    def _ollama_component(self) -> ComponentVersionDataModel:
        executable = shutil.which("ollama")
        version = self._command_version([executable, "--version"]) if executable else None
        latest = self._ollama_latest() if version else None
        path = self._brew_prefix("ollama") or self._path(executable)
        return self._row("Ollama", version, latest, path)

    def _row(
        self,
        component: str,
        version: str | None,
        latest: str | None,
        path: Path | None,
    ) -> ComponentVersionDataModel:
        installed = self._normalize_version(version)
        available = self._normalize_version(latest)
        update = (
            available
            if installed and available and installed != available
            else self.NO_UPDATE
        )
        return ComponentVersionDataModel(
            component=component,
            version=installed or self.NOT_INSTALLED,
            update=update,
            size=(
                self.format_bytes(self._disk_bytes(path))
                if installed and path is not None
                else "-"
            ),
        )

    def _npm_latest(self, package: str) -> str | None:
        npm = shutil.which("npm")
        if npm is None:
            return None
        return self._command_version(
            [npm, "view", package, "version", "--silent"]
        )

    def _ollama_latest(self) -> str | None:
        curl = shutil.which("curl")
        if curl is None:
            return None
        output = self._command_output(
            [curl, "-fsSL", "--connect-timeout", "3", "--max-time", "8", self.GITHUB_API_OLLAMA]
        )
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return None
        return self._normalize_version(
            str(data.get("tag_name") or "") if isinstance(data, dict) else ""
        )

    def _brew_latest(self, formula: str) -> str | None:
        brew = shutil.which("brew")
        if brew is None:
            return None
        environment = dict(os.environ)
        environment["HOMEBREW_NO_AUTO_UPDATE"] = "1"
        output = self._command_output(
            [brew, "info", "--json=v2", formula], environment=environment
        )
        try:
            data = json.loads(output)
            formulae = data.get("formulae", [])
            stable = formulae[0].get("versions", {}).get("stable")
        except (AttributeError, IndexError, json.JSONDecodeError, TypeError):
            return None
        return self._normalize_version(str(stable or ""))

    def _brew_installed_version(self, formula: str) -> str | None:
        brew = shutil.which("brew")
        if brew is None:
            return None
        output = self._command_output([brew, "list", "--versions", formula])
        if not output:
            return None
        fields = output.split()
        return self._normalize_version(fields[-1] if len(fields) > 1 else "")

    def _brew_prefix(self, formula: str) -> Path | None:
        brew = shutil.which("brew")
        if brew is None:
            return None
        installed = self.process_runner.run(
            [brew, "list", "--formula", formula], capture_output=True
        )
        if installed.failed:
            return None
        value = self._command_output([brew, "--prefix", formula])
        path = Path(value) if value else None
        return path if path and path.exists() else None

    def _npm_package_path(self, package: str) -> Path | None:
        npm = shutil.which("npm")
        if npm is None:
            return None
        root = self._command_output([npm, "root", "-g"])
        path = Path(root) / package if root else None
        return path if path and path.exists() else None

    def _command_version(self, command: Sequence[str | None]) -> str | None:
        output = self._command_output([value for value in command if value])
        return self._normalize_version(output)

    def _command_output(
        self,
        command: Sequence[str],
        *,
        environment: dict[str, str] | None = None,
    ) -> str:
        if not command:
            return ""
        result = self.process_runner.run(
            command,
            capture_output=True,
            env=environment,
            timeout=self.UPDATE_TIMEOUT_SECONDS,
        )
        output = result.stdout.strip() or result.stderr.strip()
        return output.splitlines()[-1] if result.succeeded and output else ""

    def _disk_bytes(self, path: Path | None) -> int:
        if path is None or (not path.exists() and not path.is_symlink()):
            return 0
        du = shutil.which("du")
        if du:
            result = self.process_runner.run(
                [du, "-skL", str(path)], capture_output=True
            )
            first = result.stdout.split(maxsplit=1)[0] if result.stdout else ""
            if result.succeeded and first.isdigit():
                return int(first) * 1024
        try:
            return path.stat().st_size if path.is_file() else 0
        except OSError:
            return 0

    @classmethod
    def _normalize_version(cls, value: str | None) -> str | None:
        match = cls.VERSION_PATTERN.search(value or "")
        return match.group(1) if match else None

    @staticmethod
    def _path(value: str | None) -> Path | None:
        return Path(value) if value else None

    @staticmethod
    def format_bytes(size: int) -> str:
        value = float(max(size, 0))
        units = ("B", "KB", "MB", "GB", "TB")
        for unit in units:
            if value < 1000 or unit == units[-1]:
                return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
            value /= 1000
        return "0 B"
