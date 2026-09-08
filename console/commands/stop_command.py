from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName


@dataclass(frozen=True, slots=True)
class StopCommand(CLICommand):
    model: str | None
    name: ClassVar[CommandName] = CommandName.STOP
