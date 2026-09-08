from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.enums.exit_code import ExitCode


CommandT = TypeVar("CommandT", bound=CLICommand)


class CommandHandler(ABC, Generic[CommandT]):
    """Execute one immutable console command DTO."""

    command_type: ClassVar[type[CLICommand]]

    @abstractmethod
    def handle(self, command: CommandT) -> ExitCode:
        """Execute the command and return its process exit code."""
