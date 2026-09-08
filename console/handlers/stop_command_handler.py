from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.stop_command import StopCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class StopCommandHandler(CommandHandler[StopCommand]):
    command_type: ClassVar[type[CLICommand]] = StopCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.support = support

    def handle(self, command: StopCommand) -> ExitCode:
        model = self.support.resolve_model(command.model)
        self.support.require_ready()
        self.console.write(f"Stopping model: {model}")
        result = self.ollama.stop_model(model)
        if result.failed:
            raise CLIError(
                result.stderr.strip() or f"Could not stop model: {model}",
                ExitCode.ERROR,
            )
        self.console.write(f"OK  Model stopped: {model}")
        return ExitCode.SUCCESS
