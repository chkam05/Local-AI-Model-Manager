import os
from pathlib import Path
import platform
import shutil
from typing import Callable, ClassVar, TextIO

from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.core.destructive_path_validator import DestructivePathValidator
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.enums.purge_component import PurgeComponent


class PurgeService:
    """Remove explicitly selected AI toolchain components and model data."""

    ENV_FORCE: ClassVar[str] = "AI_PURGE_FORCE"
    FORCE_VALUE: ClassVar[str] = "1"

    DESCRIPTIONS: ClassVar[dict[PurgeComponent | None, str]] = {
        None: "remove Ollama and all downloaded Ollama models",
        PurgeComponent.ALL: (
            "remove Ollama, all model data, Codex CLI, npm, dialog and "
            "Draw Things CLI"
        ),
        PurgeComponent.CODEX: "remove Codex CLI only",
        PurgeComponent.DIALOG: "remove dialog only",
        PurgeComponent.DRAW_THINGS_CLI: "remove Draw Things CLI only",
        PurgeComponent.DRAW_THINGS_MODELS: "remove all Draw Things model data",
        PurgeComponent.MODELS: "remove all downloaded Ollama models",
        PurgeComponent.NPM: "remove the npm CLI while keeping Node.js",
        PurgeComponent.OLLAMA: (
            "remove Ollama while preserving downloaded model data"
        ),
        PurgeComponent.OLLAMA_MODELS: "remove all downloaded Ollama models",
    }

    def __init__(
        self,
        process_runner: ProcessRunner,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        settings_storage: SettingsStorage,
    ) -> None:
        self.process_runner = process_runner
        self.ollama = ollama
        self.draw_things = draw_things
        self.settings_storage = settings_storage

    def run(
        self,
        component: PurgeComponent | None,
        *,
        stdin: TextIO,
        write: Callable[[str], None],
        warning: Callable[[str], None],
        confirmed: bool = False,
    ) -> None:
        if not confirmed and not self._confirm(component, stdin, write):
            write("Purge cancelled.")
            return
        self._validate_destructive_directories(component)
        if component is PurgeComponent.ALL:
            self._purge_codex(write, warning)
            self._purge_npm(write, warning)
            self._purge_dialog(write, warning)
            self._purge_draw_things_cli(write, warning)
            self._purge_draw_things_models(write)
            self._purge_ollama(remove_models=True, write=write, warning=warning)
            settings_directory = DestructivePathValidator.directory(
                self.settings_storage.directory, "settings directory"
            )
            self._remove_path(settings_directory)
            write("OK  Full AI console toolchain purge complete.")
        elif component is PurgeComponent.CODEX:
            self._purge_codex(write, warning)
        elif component is PurgeComponent.DIALOG:
            self._purge_dialog(write, warning)
        elif component is PurgeComponent.DRAW_THINGS_CLI:
            self._purge_draw_things_cli(write, warning)
        elif component is PurgeComponent.DRAW_THINGS_MODELS:
            self._purge_draw_things_models(write)
        elif component in {PurgeComponent.MODELS, PurgeComponent.OLLAMA_MODELS}:
            self._purge_ollama_models(write, warning)
        elif component is PurgeComponent.NPM:
            self._purge_npm(write, warning)
        elif component is PurgeComponent.OLLAMA:
            self._purge_ollama(remove_models=False, write=write, warning=warning)
        else:
            self._purge_ollama(remove_models=True, write=write, warning=warning)

    def _validate_destructive_directories(
        self, component: PurgeComponent | None
    ) -> None:
        if component in {
            None,
            PurgeComponent.ALL,
            PurgeComponent.MODELS,
            PurgeComponent.OLLAMA_MODELS,
        }:
            self._validated_ollama_models_directory()
        if component in {
            PurgeComponent.ALL,
            PurgeComponent.DRAW_THINGS_MODELS,
        }:
            DestructivePathValidator.directory(
                self.draw_things.models_directory,
                "Draw Things models directory",
            )
        if component is PurgeComponent.ALL:
            DestructivePathValidator.directory(
                self.settings_storage.directory, "settings directory"
            )

    def _confirm(
        self,
        component: PurgeComponent | None,
        stdin: TextIO,
        write: Callable[[str], None],
    ) -> bool:
        if os.environ.get(self.ENV_FORCE) == self.FORCE_VALUE:
            return True
        if not stdin.isatty():
            return False
        write(f"WARNING: This will {self.DESCRIPTIONS[component]}.")
        write("Continue with purge? [y/N]:")
        return stdin.readline().strip().casefold() == "y"

    def _purge_ollama_models(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        if self.ollama.is_available():
            try:
                self.ollama.ensure_ready()
                models = self.ollama.list_models()
                failed_models: list[str] = []
                for model in models:
                    self.ollama.stop_model(model.name)
                    result = self.ollama.uninstall_model(model.name)
                    if result.failed:
                        warning(f"Could not remove Ollama model: {model.name}")
                        failed_models.append(model.name)
                if failed_models:
                    warning(
                        "Falling back to removal of the Ollama model store; "
                        "CLI removal failed for: "
                        + ", ".join(failed_models)
                    )
            except Exception as error:
                warning(
                    "Ollama API unavailable; removing its model store: "
                    f"{error}"
                )
        self._remove_path(self._validated_ollama_models_directory())
        settings = self.settings_storage.load()
        settings.base_model = None
        self.settings_storage.save(settings)
        write("OK  All Ollama models were removed.")

    def _validated_ollama_models_directory(self) -> Path:
        return DestructivePathValidator.directory(
            self.ollama.models_directory, "OLLAMA_MODELS directory"
        )

    def _purge_ollama(
        self,
        *,
        remove_models: bool,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        if remove_models:
            self._purge_ollama_models(write, warning)
        system = platform.system()
        if system == "Darwin":
            self._run_optional(["osascript", "-e", 'tell application "Ollama" to quit'])
            self._run_optional(["pkill", "-x", "Ollama"])
            self._run_optional(["pkill", "-x", "ollama"])
            self._uninstall_brew_package("ollama-app", cask=True)
            self._uninstall_brew_package("ollama", cask=False)
            self._remove_privileged(Path("/Applications/Ollama.app"))
            self._remove_privileged(Path("/usr/local/bin/ollama"))
            for path in (
                Path.home() / "Library/Application Support/Ollama",
                Path.home() / "Library/Saved Application State/com.electron.ollama.savedState",
                Path.home() / "Library/Caches/com.electron.ollama",
                Path.home() / "Library/Caches/ollama",
                Path.home() / "Library/WebKit/com.electron.ollama",
            ):
                self._remove_path(path)
        elif system == "Linux":
            self._run_optional(["sudo", "systemctl", "stop", "ollama"])
            self._run_optional(["sudo", "systemctl", "disable", "ollama"])
            self._remove_privileged(Path("/etc/systemd/system/ollama.service"))
            self._remove_privileged(Path("/etc/systemd/system/ollama.service.d"))
            self._run_optional(["sudo", "systemctl", "daemon-reload"])
            self._run_optional(["pkill", "-x", "ollama"])
            executable = shutil.which("ollama")
            if executable in {"/usr/local/bin/ollama", "/usr/bin/ollama", "/bin/ollama"}:
                self._remove_privileged(Path(executable))
            elif executable:
                warning(f"Ollama in a custom location was preserved: {executable}")
            for path in (
                Path("/usr/local/lib/ollama"),
                Path("/usr/lib/ollama"),
                Path("/lib/ollama"),
            ):
                self._remove_privileged(path)
        else:
            raise RuntimeError("Ollama purge supports macOS and Linux only.")
        if remove_models:
            self._remove_path(Path.home() / ".ollama")
            if system == "Linux":
                self._remove_privileged(Path("/usr/share/ollama"))
        write(
            "OK  Ollama and its models were removed."
            if remove_models
            else "OK  Ollama was removed; model data was preserved."
        )

    def _purge_codex(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        codex = shutil.which("codex")
        if codex is None:
            write("OK  Codex CLI is not installed.")
            return
        npm = shutil.which("npm")
        if npm and self.process_runner.run(
            [npm, "list", "-g", "--depth=0", "@openai/codex"],
            capture_output=True,
        ).succeeded:
            result = self._run_npm_global(
                npm, ["uninstall", "-g", "@openai/codex"]
            )
            if result.failed:
                raise RuntimeError(
                    result.stderr.strip() or "Could not remove Codex CLI."
                )
        elif self._uninstall_brew_package("codex", cask=True) or self._uninstall_brew_package("codex", cask=False):
            pass
        else:
            path = Path(codex)
            recognized = {
                Path.home() / ".local/bin/codex",
                Path.home() / "bin/codex",
                Path("/usr/local/bin/codex"),
                Path("/opt/homebrew/bin/codex"),
            }
            if path not in recognized:
                raise RuntimeError(
                    f"Codex is in an unrecognized location and was preserved: {path}"
                )
            if path.is_relative_to(Path.home()):
                self._remove_path(path)
            else:
                warning(f"Removing standalone Codex command: {path}")
                self._remove_privileged(path)
        write("OK  Codex CLI was removed.")

    def _purge_npm(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        npm = shutil.which("npm")
        if npm is None:
            write("OK  npm is not installed.")
            return
        result = self._run_npm_global(npm, ["uninstall", "npm", "-g"])
        if result.failed:
            raise RuntimeError(result.stderr.strip() or "Could not remove npm.")
        if shutil.which("npm"):
            warning("Another npm command may still be available in PATH.")
        write("OK  npm CLI was removed; Node.js was preserved.")

    def _purge_draw_things_cli(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        if self._uninstall_brew_package("draw-things-cli", cask=False):
            write("OK  Draw Things CLI was removed.")
        elif shutil.which(self.draw_things.EXECUTABLE):
            warning("Draw Things CLI is not managed by Homebrew and was preserved.")
        else:
            write("OK  Draw Things CLI is not installed.")

    def _purge_dialog(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        dialog = shutil.which("dialog")
        if dialog is None:
            write("OK  dialog is not installed.")
            return
        system = platform.system()
        if system == "Darwin":
            if self._uninstall_brew_package("dialog", cask=False):
                write("OK  dialog was removed.")
            else:
                warning(
                    f"dialog is not managed by Homebrew and was preserved: {dialog}"
                )
            return
        if system == "Linux":
            managers = (
                ("apt-get", ["remove", "-y", "dialog"]),
                ("dnf", ["remove", "-y", "dialog"]),
                ("yum", ["remove", "-y", "dialog"]),
                ("pacman", ["-R", "--noconfirm", "dialog"]),
                ("zypper", ["--non-interactive", "remove", "dialog"]),
            )
            for manager, arguments in managers:
                executable = shutil.which(manager)
                if executable is None:
                    continue
                prefix = [] if os.geteuid() == 0 else ["sudo"]
                result = self.process_runner.run(
                    [*prefix, executable, *arguments]
                )
                if result.failed:
                    raise RuntimeError(
                        result.stderr.strip()
                        or f"Could not remove dialog with {manager}."
                    )
                write("OK  dialog was removed.")
                return
            warning(
                f"No supported package manager found; dialog was preserved: {dialog}"
            )
            return
        warning(f"Unsupported operating system; dialog was preserved: {dialog}")

    def _purge_draw_things_models(self, write: Callable[[str], None]) -> None:
        DestructivePathValidator.directory(
            self.draw_things.models_directory,
            "Draw Things models directory",
        )
        for path in self.draw_things.managed_model_files():
            self._remove_path(path)
        self._remove_path(self.draw_things.dependency_registry_file)
        write("OK  Draw Things model data was removed.")

    def _uninstall_brew_package(self, package: str, *, cask: bool) -> bool:
        brew = shutil.which("brew")
        if brew is None:
            return False
        kind = "--cask" if cask else "--formula"
        installed = self.process_runner.run(
            [brew, "list", kind, package], capture_output=True
        ).succeeded
        if installed:
            result = self.process_runner.run(
                [brew, "uninstall", kind, package]
            )
            if result.failed:
                raise RuntimeError(
                    result.stderr.strip()
                    or f"Could not uninstall Homebrew package: {package}"
                )
            return True
        return False

    def _run_npm_global(self, npm: str, arguments: list[str]):
        prefix_result = self.process_runner.run(
            [npm, "config", "get", "prefix"], capture_output=True
        )
        prefix = Path(prefix_result.stdout.strip()).expanduser()
        writable = prefix_result.succeeded and (
            os.access(prefix, os.W_OK)
            or (not prefix.exists() and os.access(prefix.parent, os.W_OK))
            or prefix == Path.home()
            or Path.home() in prefix.parents
        )
        command = [npm, *arguments]
        if not writable and shutil.which("sudo"):
            command.insert(0, "sudo")
        return self.process_runner.run(command)

    def _remove_privileged(self, path: Path) -> None:
        if not path.exists() and not path.is_symlink():
            return
        command = ["rm", "-rf" if path.is_dir() and not path.is_symlink() else "-f", str(path)]
        if not os.access(path.parent, os.W_OK) and shutil.which("sudo"):
            command.insert(0, "sudo")
        result = self.process_runner.run(command, capture_output=True)
        if result.failed:
            raise RuntimeError(result.stderr.strip() or f"Could not remove: {path}")

    def _run_optional(self, command: list[str]) -> None:
        if shutil.which(command[0]) is not None:
            self.process_runner.run(command, capture_output=True)

    @staticmethod
    def _remove_path(path: Path) -> None:
        if path.is_symlink() or path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path)

    @classmethod
    def _clear_directory(cls, directory: Path) -> None:
        resolved = directory.expanduser().resolve()
        if resolved in {Path("/"), Path.home().resolve()}:
            raise RuntimeError(f"Refusing to clear unsafe directory: {resolved}")
        if not resolved.is_dir():
            return
        for child in resolved.iterdir():
            cls._remove_path(child)

    @classmethod
    def _clear_draw_things_models_directory(cls, directory: Path) -> None:
        """Remove model artifacts while preserving unrelated directory data."""
        resolved = directory.expanduser().resolve()
        if resolved in {Path("/"), Path.home().resolve()}:
            raise RuntimeError(f"Refusing to clear unsafe directory: {resolved}")
        if not resolved.is_dir():
            return
        model_suffixes = {".ckpt", ".safetensors"}
        for child in resolved.iterdir():
            base_name = (
                child.name.removesuffix("-tensordata")
                if child.name.endswith("-tensordata")
                else child.name
            )
            if Path(base_name).suffix.casefold() in model_suffixes:
                cls._remove_path(child)
