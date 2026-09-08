from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.set_base_command import SetBaseCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.core.storage.settings_storage import SettingsStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class SetBaseCommandHandler(CommandHandler[SetBaseCommand]):
    command_type: ClassVar[type[CLICommand]] = SetBaseCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        settings_storage: SettingsStorage,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.settings_storage = settings_storage
        self.support = support

    def handle(self, command: SetBaseCommand) -> ExitCode:
        self.support.validate_model(command.model)
        self.support.require_ready()
        if not self.ollama.is_model_installed(command.model):
            raise CLIError(
                f"Model {command.model} is not installed. Install it first "
                f"with: ai --install {command.model}",
                ExitCode.ERROR,
            )
        settings = self.settings_storage.load()
        settings.base_model = command.model
        self.settings_storage.save(settings)
        self.console.write(f"OK  Base model set to: {command.model}")
        return ExitCode.SUCCESS
