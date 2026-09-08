from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.models_refresh_command import ModelsRefreshCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.draw_things.draw_things_backend import DrawThingsBackend
from ai_models_manager.core.ollama.ollama_backend import OllamaBackend
from ai_models_manager.enums.exit_code import ExitCode


class ModelsRefreshCommandHandler(CommandHandler[ModelsRefreshCommand]):
    command_type: ClassVar[type[CLICommand]] = ModelsRefreshCommand

    def __init__(
        self,
        console: Console,
        ollama: OllamaBackend,
        draw_things: DrawThingsBackend,
    ) -> None:
        self.console = console
        self.ollama = ollama
        self.draw_things = draw_things

    def handle(self, command: ModelsRefreshCommand) -> ExitCode:
        self.console.write("Refreshing model catalogs...")
        rows = (
            ("Ollama", *self.ollama.refresh_library_models()),
            (
                "Ollama Experimental",
                *self.ollama.refresh_experimental_models(),
            ),
            ("Draw Things", *self.draw_things.refresh_catalog()),
        )
        for label, models, refreshed in rows:
            message = f"{label}: {len(models)} model(s)"
            if refreshed:
                self.console.write(f"OK  {message}")
            else:
                self.console.warning(f"WARN {message}; using cached data.")
        return ExitCode.SUCCESS
