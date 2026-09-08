from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.update_command import UpdateCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.setup_service import SetupService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class UpdateCommandHandler(CommandHandler[UpdateCommand]):
    command_type: ClassVar[type[CLICommand]] = UpdateCommand

    def __init__(self, console: Console, setup_service: SetupService) -> None:
        self.console = console
        self.setup_service = setup_service

    def handle(self, command: UpdateCommand) -> ExitCode:
        try:
            self.setup_service.run(
                self.console.write,
                self.console.warning,
                component=command.component,
            )
        except (OSError, RuntimeError, ValueError) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        return ExitCode.SUCCESS
