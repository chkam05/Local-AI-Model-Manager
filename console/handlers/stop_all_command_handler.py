from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.stop_all_command import StopAllCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class StopAllCommandHandler(CommandHandler[StopAllCommand]):
    command_type: ClassVar[type[CLICommand]] = StopAllCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.support = support

    def handle(self, command: StopAllCommand) -> ExitCode:
        self.support.require_ready()
        results = self.ollama.stop_all_models()
        if not results:
            self.console.write("OK  No running models.")
            return ExitCode.SUCCESS
        failed: list[str] = []
        for model, result in results.items():
            if result.succeeded:
                self.console.write(f"OK  Model stopped: {model}")
            else:
                self.console.warning(f"Could not stop model: {model}")
                failed.append(model)
        if failed:
            raise CLIError(
                "Could not stop all models. Failed: " + ", ".join(failed),
                ExitCode.ERROR,
            )
        self.console.write("OK  All running models stopped.")
        return ExitCode.SUCCESS
