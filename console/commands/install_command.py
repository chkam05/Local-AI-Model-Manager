from dataclasses import dataclass
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName
from ai_models_manager.enums.install_source_type import InstallSourceType
from ai_models_manager.enums.model_backend import ModelBackend


@dataclass(frozen=True, slots=True)
class InstallCommand(CLICommand):
    model: str | None
    source: str | None
    backend: ModelBackend = ModelBackend.AUTO
    source_type: InstallSourceType = InstallSourceType.AUTO
    confirmed: bool = False
    name: ClassVar[CommandName] = CommandName.INSTALL
