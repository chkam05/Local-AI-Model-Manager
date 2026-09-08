from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.run_command import RunCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.ollama_command_support import OllamaCommandSupport
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class RunCommandHandler(CommandHandler[RunCommand]):
    command_type: ClassVar[type[CLICommand]] = RunCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        support: OllamaCommandSupport,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.support = support

    def handle(self, command: RunCommand) -> ExitCode:
        model = self.support.resolve_model(command.model)
        context = self.support.parse_context_length(command.context_length)
        self.support.require_ready()
        if not self.ollama.is_model_installed(model):
            raise CLIError(
                f"Model {model} is not installed. Install it first with: "
                f"ai --install {model}",
                ExitCode.ERROR,
            )
        description = (
            "Ollama default context"
            if context is None
            else f"context: {context} tokens"
        )
        self.console.write(f"Loading {model} ({description})...")
        try:
            self.ollama.load_model(model, context)
        except OllamaBackendError as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        self.console.write(f"OK  Model is running: {model}")
        if context is not None:
            self.console.write(f"Context: {context} tokens")
        self.console.write(f"API: {self.ollama.base_url}")
        return ExitCode.SUCCESS
