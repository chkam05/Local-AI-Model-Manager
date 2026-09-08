from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName


@dataclass(frozen=True, slots=True)
class ChatCommand(CLICommand):
    model: str | None
    context_length: str | None
    session_name: str | None
    input_files: tuple[Path, ...]
    name: ClassVar[CommandName] = CommandName.CHAT
