from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.purge_command import PurgeCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.purge_service import PurgeService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class PurgeCommandHandler(CommandHandler[PurgeCommand]):
    command_type: ClassVar[type[CLICommand]] = PurgeCommand

    def __init__(self, console: Console, purge_service: PurgeService) -> None:
        self.console = console
        self.purge_service = purge_service

    def handle(self, command: PurgeCommand) -> ExitCode:
        try:
            self.purge_service.run(
                command.component,
                stdin=self.console.stdin,
                write=self.console.write,
                warning=self.console.warning,
                confirmed=command.confirmed,
            )
        except (OSError, RuntimeError, ValueError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        return ExitCode.SUCCESS
