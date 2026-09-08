from typing import ClassVar

from ai_models_manager.console.commands.clear_cache_command import ClearCacheCommand
from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.storage.cache_storage import CacheStorage
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class ClearCacheCommandHandler(CommandHandler[ClearCacheCommand]):
    command_type: ClassVar[type[CLICommand]] = ClearCacheCommand

    def __init__(self, console: Console, cache_storage: CacheStorage) -> None:
        self.console = console
        self.cache_storage = cache_storage

    def handle(self, command: ClearCacheCommand) -> ExitCode:
        try:
            removed_files = self.cache_storage.clear()
        except (OSError, RuntimeError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        if removed_files == 0:
            self.console.write("OK  Cache is already empty.")
        else:
            self.console.write(
                f"OK  Cache cleared. Removed files: {removed_files}"
            )
        return ExitCode.SUCCESS
