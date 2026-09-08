from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.uninstall_command import UninstallCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class UninstallCommandHandler(CommandHandler[UninstallCommand]):
    command_type: ClassVar[type[CLICommand]] = UninstallCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        settings_storage: SettingsStorage,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.draw_things = draw_things
        self.settings_storage = settings_storage
        self.support = support

    def handle(self, command: UninstallCommand) -> ExitCode:
        if not command.confirmed:
            self.console.write(f"Uninstall: {command.model}")
            if not self.console.confirm("Continue with removal? [y/N]: "):
                self.console.write("Removal cancelled.")
                return ExitCode.SUCCESS
        if self.draw_things.is_asset_installed(
            command.model
        ) or command.model.casefold().endswith((".ckpt", ".safetensors")):
            return self._uninstall_draw_things(
                command.model, command.dependency_mode
            )
        self.support.validate_model(command.model)
        self.support.require_ready()
        if not self.ollama.is_model_installed(command.model):
            raise CLIError(
                f"Model is not installed: {command.model}", ExitCode.ERROR
            )
        self.ollama.stop_model(command.model)
        self.console.write(f"Removing model: {command.model}")
        result = self.ollama.uninstall_model(command.model)
        if result.failed:
            raise CLIError(
                result.stderr.strip()
                or f"Could not remove model: {command.model}",
                ExitCode.ERROR,
            )
        settings = self.settings_storage.load()
        if (
            settings.base_model
            and self.ollama.normalize_model_name(settings.base_model)
            == self.ollama.normalize_model_name(command.model)
        ):
            settings.base_model = None
            self.settings_storage.save(settings)
            self.console.warning(
                "The removed model was the base model; the setting was cleared."
            )
        self.console.write(f"OK  Model uninstalled: {command.model}")
        return ExitCode.SUCCESS

    def _uninstall_draw_things(self, model: str, dependency_mode: str) -> ExitCode:
        if not self.draw_things.is_valid_file_name(model):
            raise CLIUsageError(f"Invalid Draw Things file name: {model}")
        if not self.draw_things.is_asset_installed(model):
            raise CLIError(
                f"Draw Things asset is not installed: {model}", ExitCode.ERROR
            )
        plan = self.draw_things.build_removal_plan(
            model, dependency_mode=dependency_mode
        )
        try:
            result = self.draw_things.execute_removal_plan(plan)
        except (OSError, RuntimeError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if result.removed_files == 0:
            if result.kept_dependencies:
                raise CLIError(
                    "Draw Things dependency is still used by an installed "
                    f"model: {model}",
                    ExitCode.ERROR,
                )
            raise CLIError(
                f"Could not remove Draw Things asset: {model}", ExitCode.ERROR
            )
        for dependency in result.removed_dependencies:
            self.console.write(
                f"OK  Unused Draw Things dependency removed: {dependency}"
            )
        if result.kept_dependencies:
            self.console.warning(
                "Shared Draw Things dependencies kept: "
                + ", ".join(result.kept_dependencies)
            )
        self.console.write(f"OK  Draw Things asset removed: {model}")
        return ExitCode.SUCCESS
