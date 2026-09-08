from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.install_command import InstallCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.disk_space_service import DiskSpaceService
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.enums.install_source_type import InstallSourceType
from ai_models_manager.enums.model_backend import ModelBackend
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class InstallCommandHandler(CommandHandler[InstallCommand]):
    command_type: ClassVar[type[CLICommand]] = InstallCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        support: OllamaCommandSupport,
        disk_space: DiskSpaceService,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.draw_things = draw_things
        self.support = support
        self.disk_space = disk_space

    def handle(self, command: InstallCommand) -> ExitCode:
        target = command.source or command.model
        if target is not None and not command.confirmed:
            self.console.write(f"Install: {target}")
            if not self.console.confirm("Continue with installation? [y/N]: "):
                self.console.write("Installation cancelled.")
                return ExitCode.SUCCESS
        if command.source is not None:
            return self._install_source(
                command.source, command.backend, command.source_type
            )
        if command.model is None:
            raise CLIUsageError("Missing model or --source.")
        backend = command.backend
        if backend is ModelBackend.AUTO:
            backend = (
                ModelBackend.DRAW_THINGS
                if command.model.casefold().endswith((".ckpt", ".safetensors"))
                else ModelBackend.OLLAMA
            )
        if backend is ModelBackend.DRAW_THINGS:
            return self._install_draw_things_model(command.model)
        self.support.validate_model(command.model)
        self.support.require_ready()
        if self.ollama.is_model_installed(command.model):
            self.console.warning(
                f"Model {command.model} is already installed; checking for updates."
            )
        self._check_disk_space(
            self.ollama.models_directory,
            self._ollama_model_size(command.model),
            command.model,
        )
        self.console.write(f"Downloading model: {command.model}")
        result = self.ollama.install_model(command.model)
        if result.failed:
            raise CLIError(
                result.stderr.strip()
                or f"Could not install model: {command.model}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Model installed: {command.model}")
        return ExitCode.SUCCESS

    def _install_source(
        self,
        source: str,
        backend: ModelBackend,
        source_type: InstallSourceType,
    ) -> ExitCode:
        selected_backend = backend
        lowered = source.split("?", 1)[0].split("#", 1)[0].casefold()
        if selected_backend is ModelBackend.AUTO:
            selected_backend = (
                ModelBackend.DRAW_THINGS
                if source_type is InstallSourceType.LORA
                or lowered.endswith((".ckpt", ".safetensors"))
                else ModelBackend.OLLAMA
            )
        if (
            source_type is InstallSourceType.LORA
            and selected_backend is not ModelBackend.DRAW_THINGS
        ):
            raise CLIUsageError(
                "LoRA sources are supported only by --backend draw-things."
            )
        if selected_backend is ModelBackend.DRAW_THINGS:
            if not self.draw_things.is_available():
                raise CLIError(
                    "Draw Things CLI is not installed. Run: ai --setup",
                    ExitCode.ERROR,
                )
            resolved_type = source_type
            if resolved_type is InstallSourceType.AUTO:
                resolved_type = (
                    InstallSourceType.LORA
                    if any(
                        token in lowered
                        for token in ("lora", "lycoris", "adapter")
                    )
                    else InstallSourceType.MODEL
                )
            self._check_disk_space(
                self.draw_things.models_directory,
                self.disk_space.source_size(source),
                source,
            )
            self.console.write(f"Importing Draw Things source: {source}")
            try:
                result = self.draw_things.install_source(
                    source,
                    lora=resolved_type is InstallSourceType.LORA,
                    checksum_verified=self._checksum_verified,
                )
            except (OSError, ValueError) as error:
                raise CLIError(str(error), ExitCode.ERROR) from error
            description = (
                "LoRA"
                if resolved_type is InstallSourceType.LORA
                else "model"
            )
        else:
            self.support.require_ready()
            self._check_disk_space(
                self.ollama.models_directory,
                self.disk_space.source_size(source),
                source,
            )
            self.console.write(f"Importing Ollama source: {source}")
            try:
                description, result = self.ollama.install_source(
                    source,
                    checksum_verified=self._checksum_verified,
                )
            except (OSError, ValueError) as error:
                raise CLIError(str(error), ExitCode.ERROR) from error
        if result.failed:
            raise CLIError(
                result.stderr.strip() or f"Could not import source: {source}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Source installed as {description}.")
        return ExitCode.SUCCESS

    def _install_draw_things_model(self, model: str) -> ExitCode:
        if not self.draw_things.is_valid_file_name(model):
            raise CLIUsageError(f"Invalid Draw Things model file: {model}")
        if not self.draw_things.is_available():
            raise CLIError(
                "Draw Things CLI is not installed. Run: ai --setup",
                ExitCode.ERROR,
            )
        display_name = self.draw_things.catalog_name(model) or model
        if self.draw_things.is_asset_installed(model):
            self.console.warning(
                f"Draw Things model is already installed: {display_name}"
            )
        self._check_disk_space(
            self.draw_things.models_directory,
            self.draw_things.catalog_size(model),
            display_name,
        )
        self.console.write(f"Downloading Draw Things model: {display_name}")
        result = self.draw_things.install_model(model)
        if result.failed:
            raise CLIError(
                result.stderr.strip()
                or f"Could not install Draw Things model: {display_name}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Draw Things model installed: {display_name}")
        return ExitCode.SUCCESS

    def _checksum_verified(self, file_name: str) -> None:
        self.console.write(f"OK  SHA-256 checksum verified: {file_name}")

    def _ollama_model_size(self, model: str) -> int:
        sizes = {
            **self.ollama.library_model_sizes(),
            **self.ollama.experimental_model_sizes(),
        }
        target = self.ollama.normalize_model_name(model)
        return next(
            (
                size
                for name, size in sizes.items()
                if self.ollama.normalize_model_name(name) == target
            ),
            0,
        )

    def _check_disk_space(
        self,
        destination,
        required_bytes: int,
        target: str,
    ) -> None:
        if required_bytes <= 0:
            return
        try:
            check = self.disk_space.check(destination, required_bytes)
        except OSError as error:
            raise CLIError(
                f"Could not check free space for {destination}: {error}",
                ExitCode.ERROR,
            ) from error
        required = self.disk_space.format_size(check.required_bytes)
        available = self.disk_space.format_size(check.available_bytes)
        reserve = self.disk_space.format_size(check.reserve_bytes)
        self.console.write(
            f"Disk space for {target}: {required} download, "
            f"{available} available ({reserve} reserve)."
        )
        if not check.sufficient:
            total = self.disk_space.format_size(check.total_required_bytes)
            raise CLIError(
                f"Not enough free space in {check.destination}: "
                f"{total} required including reserve, {available} available.",
                ExitCode.ERROR,
            )
