from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.update_model_command import UpdateModelCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class UpdateModelCommandHandler(CommandHandler[UpdateModelCommand]):
    command_type: ClassVar[type[CLICommand]] = UpdateModelCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.draw_things = draw_things
        self.support = support

    def handle(self, command: UpdateModelCommand) -> ExitCode:
        backend = self._backend(command.model)
        if not command.confirmed:
            self.console.write(f"Update model: {command.model}")
            if not self.console.confirm("Continue with update? [y/N]: "):
                self.console.write("Model update cancelled.")
                return ExitCode.SUCCESS
        if backend == "Draw Things":
            return self._update_draw_things(command.model)
        return self._update_ollama(command.model)

    def _backend(self, model: str) -> str:
        if self.draw_things.is_asset_installed(model):
            return "Draw Things"
        self.support.validate_model(model)
        self.support.require_ready()
        if not self.ollama.is_model_installed(model):
            raise CLIError(f"Model is not installed: {model}", ExitCode.ERROR)
        return "Ollama"

    def _update_ollama(self, model: str) -> ExitCode:
        self.console.write(f"Updating Ollama model: {model}")
        result = self.ollama.install_model(model)
        if result.failed:
            raise CLIError(
                result.stderr.strip() or f"Could not update model: {model}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Model updated: {model}")
        return ExitCode.SUCCESS

    def _update_draw_things(self, model: str) -> ExitCode:
        if not self.draw_things.is_valid_file_name(model):
            raise CLIUsageError(f"Invalid Draw Things model file: {model}")
        display_name = self.draw_things.catalog_name(model)
        if display_name is None:
            raise CLIError(
                "This local Draw Things model has no catalog source and "
                "cannot be updated automatically.",
                ExitCode.ERROR,
            )
        if not self.draw_things.is_available():
            raise CLIError(
                "Draw Things CLI is not installed. Run: ai --setup",
                ExitCode.ERROR,
            )
        self.console.write(f"Updating Draw Things model: {display_name}")
        result = self.draw_things.install_model(model)
        if result.failed:
            raise CLIError(
                result.stderr.strip()
                or f"Could not update Draw Things model: {display_name}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Model updated: {display_name}")
        return ExitCode.SUCCESS
