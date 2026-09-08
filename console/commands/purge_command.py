from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName
from ai_models_manager.enums.purge_component import PurgeComponent


@dataclass(frozen=True, slots=True)
class PurgeCommand(CLICommand):
    component: PurgeComponent | None
    confirmed: bool = False
    name: ClassVar[CommandName] = CommandName.PURGE
