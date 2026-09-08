from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName


@dataclass(frozen=True, slots=True)
class ToolCommand(CLICommand):
    tool: str
    enabled: bool
    name: ClassVar[CommandName] = CommandName.TOOL
