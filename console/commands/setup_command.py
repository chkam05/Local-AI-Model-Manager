from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName
from ai_models_manager.enums.setup_component import SetupComponent


@dataclass(frozen=True, slots=True)
class SetupCommand(CLICommand):
    component: SetupComponent | None = None
    name: ClassVar[CommandName] = CommandName.SETUP
