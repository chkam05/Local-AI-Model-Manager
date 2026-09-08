from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName
from ai_models_manager.enums.list_target import ListTarget
from ai_models_manager.enums.sort_direction import SortDirection


@dataclass(frozen=True, slots=True)
class ListCommand(CLICommand):
    target: ListTarget = ListTarget.LOCAL
    order: tuple[str, ...] = ("model",)
    direction: SortDirection = SortDirection.AUTO
    dependencies: bool = False
    name: ClassVar[CommandName] = CommandName.MODELS
