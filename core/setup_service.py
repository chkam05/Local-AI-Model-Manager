import json
import os
from pathlib import Path
import platform
import re
import shutil
import tempfile
from typing import Callable, ClassVar, Mapping

from ai_models_manager.console.models.process_result import ProcessResult
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.enums.setup_component import SetupComponent


class SetupService:
    """Install or update dependencies required by the console application."""

    CODEX_PACKAGE: ClassVar[str] = "@openai/codex"
    CODEX_EXECUTABLE: ClassVar[str] = "codex"
    CURL_EXECUTABLE: ClassVar[str] = "curl"
    DIALOG_EXECUTABLE: ClassVar[str] = "dialog"
    DRAW_THINGS_EXECUTABLE: ClassVar[str] = "draw-things-cli"
    GITHUB_API_OLLAMA: ClassVar[str] = (
        "https://api.github.com/repos/ollama/ollama/releases/latest"
    )
    HOMEBREW_INSTALL_URL: ClassVar[str] = (
        "https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"
    )
    HOMEBREW_PATHS: ClassVar[tuple[Path, ...]] = (
        Path("/opt/homebrew/bin/brew"),
        Path("/usr/local/bin/brew"),
        Path("/home/linuxbrew/.linuxbrew/bin/brew"),
    )
    IMAGEMAGICK_EXECUTABLES: ClassVar[tuple[str, ...]] = (
        "magick",
        "montage",
    )
    IMAGEMAGICK_PACKAGE: ClassVar[str] = "imagemagick"
    NPM_EXECUTABLE: ClassVar[str] = "npm"
    NVM_INSTALL_URL: ClassVar[str] = (
        "https://raw.githubusercontent.com/nvm-sh/nvm/master/install.sh"
    )
    OLLAMA_EXECUTABLE: ClassVar[str] = "ollama"
    OLLAMA_INSTALL_URL: ClassVar[str] = "https://ollama.com/install.sh"
    SHELL_EXECUTABLE: ClassVar[str] = "/bin/bash"
    COMMAND_TIMEOUT_SECONDS: ClassVar[int] = 30
    DOWNLOAD_TIMEOUT_SECONDS: ClassVar[int] = 120
    INSTALL_TIMEOUT_SECONDS: ClassVar[int] = 1800
    VERSION_PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"(?<!\d)(\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?)"
    )

    def __init__(self, process_runner: ProcessRunner) -> None:
        self.process_runner = process_runner

    def run(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
        component: SetupComponent | None = None,
    ) -> None:
        if platform.system() not in {"Darwin", "Linux"}:
            raise RuntimeError("--setup currently supports macOS and Linux only.")
        if shutil.which(self.CURL_EXECUTABLE) is None:
            raise RuntimeError("curl is required by --setup.")

        if component is not None:
            write(f"Updating toolchain component: {component.value}")
            self._run_component(component, write, warning)
            write(f"\nOK  Component is ready: {component.value}.")
            return

        write("AI console toolchain setup")
        write("\n[1/6] Checking Ollama...")
        self._setup_ollama(write, warning)
        write("\n[2/6] Checking Node.js and npm...")
        npm, environment = self._setup_npm(write, warning)
        write("\n[3/6] Checking Codex CLI...")
        self._setup_codex(npm, environment, write, warning)
        write("\n[4/6] Checking dialog...")
        self._setup_dialog(write, warning)
        write("\n[5/6] Checking Draw Things CLI...")
        self._setup_draw_things_cli(write, warning)
        write("\n[6/6] Checking ImageMagick...")
        self._setup_imagemagick(write)
        write("\nOK  AI console toolchain setup is complete.")

    def _run_component(
        self,
        component: SetupComponent,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        if component is SetupComponent.OLLAMA:
            self._setup_ollama(write, warning)
        elif component is SetupComponent.NPM:
            self._setup_npm(write, warning)
        elif component is SetupComponent.CODEX:
            npm, environment = self._setup_npm(
                write, warning, update=False
            )
            self._setup_codex(npm, environment, write, warning)
        elif component is SetupComponent.DIALOG:
            self._setup_dialog(write, warning)
        elif component is SetupComponent.DRAW_THINGS_CLI:
            self._setup_draw_things_cli(write, warning)
        elif component is SetupComponent.IMAGEMAGICK:
            self._setup_imagemagick(write)

    def _setup_imagemagick(self, write: Callable[[str], None]) -> None:
        system = platform.system()
        if system == "Darwin":
            brew = self._find_homebrew() or self._install_homebrew(write)
            self._brew_install_or_update(
                brew, self.IMAGEMAGICK_PACKAGE, write
            )
        elif system == "Linux":
            self._install_linux_package(self.IMAGEMAGICK_PACKAGE)
        else:
            raise RuntimeError(
                "ImageMagick setup supports macOS and Linux only."
            )
        executable = next(
            (
                path
                for name in self.IMAGEMAGICK_EXECUTABLES
                if (path := shutil.which(name)) is not None
            ),
            None,
        )
        version = (
            self._imagemagick_version(executable)
            if executable
            else None
        )
        if executable is None or version is None:
            raise RuntimeError(
                "ImageMagick installation finished, but magick/montage is "
                "unavailable or does not report a valid version."
            )
        write(f"OK  ImageMagick is ready (v{version}).")

    def _imagemagick_version(self, executable: str) -> str | None:
        result = self.process_runner.run(
            [executable, "--version"],
            capture_output=True,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        )
        if result.failed:
            return None
        return self._extract_version(
            "\n".join((result.stdout, result.stderr))
        )

    def _setup_ollama(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        executable = shutil.which(self.OLLAMA_EXECUTABLE)
        local = self._command_version([executable, "--version"]) if executable else None
        if executable and not local:
            raise RuntimeError(
                f"Ollama exists at {executable}, but the command does not "
                "work or does not report a valid version."
            )
        latest = self._latest_ollama_version()
        if executable and latest and local == latest:
            write(f"OK  Ollama is up to date (v{local}).")
            return
        if executable and latest is None:
            warning(
                "Could not determine the latest Ollama version; keeping "
                f"the installed version{f' v{local}' if local else ''}."
            )
            return
        if executable:
            write(f"Updating Ollama ({local or 'unknown'} -> {latest or 'latest'})...")
        else:
            write("Installing Ollama...")
        result = self._run_downloaded_script(self.OLLAMA_INSTALL_URL, "sh")
        self._require_success(result, "Ollama installer failed")
        detected = shutil.which(self.OLLAMA_EXECUTABLE)
        if detected is None:
            raise RuntimeError(
                "Ollama installation finished, but ollama is not available in PATH."
            )
        installed = self._command_version([detected, "--version"])
        if latest and installed and installed != latest:
            warning(
                f"Detected Ollama v{installed}; the latest reported version is v{latest}."
            )
        else:
            write(f"OK  Ollama is ready{f' (v{installed})' if installed else ''}.")

    def _setup_npm(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
        *,
        update: bool = True,
    ) -> tuple[str, Mapping[str, str] | None]:
        npm = shutil.which(self.NPM_EXECUTABLE)
        if npm is None:
            write("npm is missing. Installing Node.js LTS through nvm...")
            self._install_nvm_node()
            npm = self._find_nvm_executable(self.NPM_EXECUTABLE)
            if npm is None:
                raise RuntimeError(
                    "Node.js installation finished, but npm could not be located."
                )
        environment = self._environment_for(npm)
        local = self._command_output([npm, "--version"], environment)
        if not local:
            raise RuntimeError(
                f"npm exists at {npm}, but the command does not work. "
                "Repair Node.js/npm and retry."
            )
        latest = self._command_output(
            [npm, "view", "npm", "version", "--silent"], environment
        )
        if not latest:
            warning(
                "Could not determine the latest npm version; keeping the "
                f"installed version v{local}."
            )
            write(f"OK  npm is ready (v{local}).")
            return npm, environment
        if update and latest and local != latest:
            write(f"Updating npm ({local or 'unknown'} -> {latest})...")
            result = self._run_npm_global(
                npm, ["install", "-g", "npm@latest"], environment
            )
            if result.failed:
                warning("npm could not be updated; continuing with the installed version.")
            else:
                local = self._command_output([npm, "--version"], environment)
        write(f"OK  npm is ready{f' (v{local})' if local else ''}.")
        return npm, environment

    def _setup_dialog(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        system = platform.system()
        if system == "Darwin":
            brew = self._find_homebrew()
            dialog = shutil.which(self.DIALOG_EXECUTABLE)
            if dialog and not self.process_runner.run(
                [dialog, "--version"],
                capture_output=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
            ).succeeded:
                raise RuntimeError(
                    f"dialog exists at {dialog}, but the command does not work."
                )
            if dialog and (
                brew is None
                or not self.process_runner.run(
                    [brew, "list", "--formula", "dialog"],
                    capture_output=True,
                    timeout=self.COMMAND_TIMEOUT_SECONDS,
                ).succeeded
            ):
                write("OK  dialog is already installed outside Homebrew.")
                return
            brew = brew or self._install_homebrew(write)
            self._brew_install_or_update(brew, "dialog", write)
            return
        if system == "Linux":
            self._install_linux_package("dialog")
            dialog = shutil.which(self.DIALOG_EXECUTABLE)
            if dialog is None:
                raise RuntimeError(
                    "dialog installation finished, but dialog is unavailable."
                )
            if not self.process_runner.run(
                [dialog, "--version"],
                capture_output=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
            ).succeeded:
                raise RuntimeError(
                    f"dialog exists at {dialog}, but the command does not work."
                )
            write("OK  dialog is ready.")
            return
        raise RuntimeError("dialog setup supports macOS and Linux only.")

    def _setup_draw_things_cli(
        self,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        if platform.system() != "Darwin":
            executable = shutil.which(self.DRAW_THINGS_EXECUTABLE)
            if executable and self.process_runner.run(
                [executable, "--version"],
                capture_output=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
            ).succeeded:
                write("OK  Draw Things CLI is installed.")
                return
            if executable:
                raise RuntimeError(
                    f"Draw Things CLI exists at {executable}, but the command "
                    "does not work."
                )
            warning("Automatic Draw Things CLI installation is supported on macOS only.")
            raise RuntimeError(
                "Draw Things CLI is required but could not be installed "
                "automatically on this system."
            )
        brew = self._find_homebrew() or self._install_homebrew(write)
        self._brew_install_or_update(brew, "draw-things-cli", write)
        executable = shutil.which(self.DRAW_THINGS_EXECUTABLE)
        if executable is None or not self.process_runner.run(
            [executable, "--version"],
            capture_output=True,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        ).succeeded:
            raise RuntimeError(
                "Draw Things CLI is installed incompletely or is unavailable "
                "in PATH."
            )

    def _brew_install_or_update(
        self,
        brew: str,
        package: str,
        write: Callable[[str], None],
    ) -> None:
        installed = self.process_runner.run(
            [brew, "list", "--formula", package],
            capture_output=True,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        ).succeeded
        if installed:
            outdated = self.process_runner.run(
                [brew, "outdated", "--formula", package],
                capture_output=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
            )
            if package in outdated.stdout.splitlines():
                self._require_success(
                    self.process_runner.run(
                        [brew, "upgrade", package],
                        timeout=self.INSTALL_TIMEOUT_SECONDS,
                    ),
                    f"Could not update {package}",
                )
                write(f"OK  {package} was updated.")
            else:
                write(f"OK  {package} is already up to date.")
            return
        self._require_success(
            self.process_runner.run(
                [brew, "install", package],
                timeout=self.INSTALL_TIMEOUT_SECONDS,
            ),
            f"Could not install {package}",
        )
        write(f"OK  {package} was installed.")

    def _install_homebrew(self, write: Callable[[str], None]) -> str:
        if platform.system() != "Darwin":
            raise RuntimeError("Automatic Homebrew installation is supported on macOS only.")
        xcode = self.process_runner.run(
            ["xcode-select", "-p"],
            capture_output=True,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        )
        if xcode.failed:
            self.process_runner.run(
                ["xcode-select", "--install"],
                capture_output=True,
                timeout=self.COMMAND_TIMEOUT_SECONDS,
            )
            raise RuntimeError(
                "Complete the Apple Command Line Tools installation, then run the command again."
            )
        write("Installing Homebrew...")
        result = self._run_downloaded_script(
            self.HOMEBREW_INSTALL_URL, self.SHELL_EXECUTABLE
        )
        self._require_success(result, "Homebrew installer failed")
        brew = self._find_homebrew()
        if brew is None:
            raise RuntimeError(
                "Homebrew was installed but could not be located. Open a new terminal and retry."
            )
        return brew

    def _install_linux_package(self, package: str) -> None:
        managers = (
            ("apt-get", (["update"], ["install", "-y", package])),
            ("dnf", ([], ["install", "-y", package])),
            ("yum", ([], ["install", "-y", package])),
            ("pacman", ([], ["-Sy", "--needed", "--noconfirm", package])),
            ("zypper", ([], ["--non-interactive", "install", package])),
        )
        for manager, command_groups in managers:
            executable = shutil.which(manager)
            if executable is None:
                continue
            if os.geteuid() != 0 and shutil.which("sudo") is None:
                raise RuntimeError(
                    f"sudo is required to install {package} with {manager}."
                )
            prefix = [] if os.geteuid() == 0 else ["sudo"]
            for arguments in command_groups:
                if not arguments:
                    continue
                self._require_success(
                    self.process_runner.run(
                        [*prefix, executable, *arguments],
                        timeout=self.INSTALL_TIMEOUT_SECONDS,
                    ),
                    f"Could not install {package} with {manager}",
                )
            return
        raise RuntimeError(
            f"No supported package manager was found to install {package}."
        )

    @classmethod
    def _find_homebrew(cls) -> str | None:
        detected = shutil.which("brew")
        if detected:
            return detected
        return next((str(path) for path in cls.HOMEBREW_PATHS if path.is_file()), None)

    def _setup_codex(
        self,
        npm: str,
        environment: Mapping[str, str] | None,
        write: Callable[[str], None],
        warning: Callable[[str], None],
    ) -> None:
        latest = self._command_output(
            [npm, "view", self.CODEX_PACKAGE, "version", "--silent"],
            environment,
        )
        codex = shutil.which(self.CODEX_EXECUTABLE, path=(environment or os.environ).get("PATH"))
        local = self._command_version([codex, "--version"], environment) if codex else None
        if codex and not local:
            raise RuntimeError(
                f"Codex CLI exists at {codex}, but the command does not work."
            )
        if not latest:
            if codex:
                warning(
                    "Could not determine the latest Codex CLI version; "
                    f"keeping the installed version v{local}."
                )
                write(f"OK  Codex CLI is ready (v{local}).")
                return
            raise RuntimeError(
                "Could not determine the latest Codex CLI version and Codex "
                "is not installed."
            )
        if codex and local == latest:
            write(f"OK  Codex CLI is up to date (v{local}).")
            return
        write(
            "Installing Codex CLI..."
            if codex is None
            else f"Updating Codex CLI ({local or 'unknown'} -> {latest})..."
        )
        result = self._run_npm_global(
            npm,
            ["install", "-g", f"{self.CODEX_PACKAGE}@latest"],
            environment,
        )
        self._require_success(result, "Codex CLI installation failed")
        codex = shutil.which(
            self.CODEX_EXECUTABLE,
            path=(environment or os.environ).get("PATH"),
        )
        if codex is None:
            raise RuntimeError(
                "Codex CLI installation finished, but codex is not available in PATH."
            )
        installed = self._command_version([codex, "--version"], environment)
        if installed != latest:
            warning(
                f"Detected Codex CLI v{installed or 'unknown'}; expected v{latest}."
            )
        else:
            write(f"OK  Codex CLI is ready (v{installed}).")

    def _install_nvm_node(self) -> None:
        result = self._run_downloaded_script(self.NVM_INSTALL_URL, self.SHELL_EXECUTABLE)
        self._require_success(result, "nvm installer failed")
        nvm_directory = Path.home() / ".nvm"
        environment = dict(os.environ)
        environment["NVM_DIR"] = str(nvm_directory)
        result = self.process_runner.run(
            [
                self.SHELL_EXECUTABLE,
                "-lc",
                'source "$NVM_DIR/nvm.sh" && nvm install --lts --latest-npm && nvm alias default "lts/*"',
            ],
            env=environment,
            timeout=self.INSTALL_TIMEOUT_SECONDS,
        )
        self._require_success(result, "Node.js installation through nvm failed")

    def _run_downloaded_script(self, url: str, interpreter: str) -> ProcessResult:
        with tempfile.TemporaryDirectory(prefix="ai-setup-") as directory:
            installer = Path(directory) / "install.sh"
            download = self.process_runner.run(
                [self.CURL_EXECUTABLE, "-fsSL", url, "-o", str(installer)],
                capture_output=True,
                timeout=self.DOWNLOAD_TIMEOUT_SECONDS,
            )
            self._require_success(download, f"Could not download installer from {url}")
            return self.process_runner.run(
                [interpreter, str(installer)],
                timeout=self.INSTALL_TIMEOUT_SECONDS,
            )

    def _run_npm_global(
        self,
        npm: str,
        arguments: list[str],
        environment: Mapping[str, str] | None,
    ) -> ProcessResult:
        prefix_value = self._command_output(
            [npm, "config", "get", "prefix"], environment
        )
        prefix = Path(prefix_value).expanduser() if prefix_value else None
        writable = bool(
            prefix
            and (
                (prefix.exists() and os.access(prefix, os.W_OK))
                or (
                    not prefix.exists()
                    and prefix.parent.exists()
                    and os.access(prefix.parent, os.W_OK)
                )
                or prefix == Path.home()
                or Path.home() in prefix.parents
            )
        )
        command = [npm, *arguments]
        if not writable and shutil.which("sudo") is not None:
            command.insert(0, "sudo")
        return self.process_runner.run(
            command,
            env=environment,
            timeout=self.INSTALL_TIMEOUT_SECONDS,
        )

    def _latest_ollama_version(self) -> str | None:
        output = self._command_output(
            [self.CURL_EXECUTABLE, "-fsSL", self.GITHUB_API_OLLAMA]
        )
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            return None
        tag = data.get("tag_name") if isinstance(data, dict) else None
        return self._extract_version(str(tag or ""))

    def _command_version(
        self,
        command: list[str | None],
        environment: Mapping[str, str] | None = None,
    ) -> str | None:
        output = self._command_output(
            [value for value in command if value is not None], environment
        )
        return self._extract_version(output)

    def _command_output(
        self,
        command: list[str],
        environment: Mapping[str, str] | None = None,
    ) -> str:
        result = self.process_runner.run(
            command,
            capture_output=True,
            env=environment,
            timeout=self.COMMAND_TIMEOUT_SECONDS,
        )
        return result.stdout.strip().splitlines()[-1] if result.succeeded and result.stdout.strip() else ""

    @classmethod
    def _extract_version(cls, value: str) -> str | None:
        match = cls.VERSION_PATTERN.search(value)
        return match.group(1) if match else None

    @staticmethod
    def _find_nvm_executable(name: str) -> str | None:
        root = Path.home() / ".nvm" / "versions" / "node"
        candidates = sorted(root.glob(f"*/bin/{name}"), reverse=True)
        return str(candidates[0]) if candidates else None

    @staticmethod
    def _environment_for(executable: str) -> dict[str, str]:
        environment = dict(os.environ)
        binary_directory = str(Path(executable).parent)
        environment["PATH"] = os.pathsep.join(
            (binary_directory, environment.get("PATH", ""))
        )
        return environment

    @staticmethod
    def _require_success(result: ProcessResult, message: str) -> None:
        if result.failed:
            details = result.stderr.strip()
            raise RuntimeError(f"{message}: {details}" if details else message)
