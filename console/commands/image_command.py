from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.command_name import CommandName


@dataclass(frozen=True, slots=True)
class ImageCommand(CLICommand):
    model: str | None
    width: int
    height: int
    output_directory: Path | None
    file_name: str | None
    prompt: str
    input_files: tuple[Path, ...]
    strength: float | None
    name: ClassVar[CommandName] = CommandName.IMAGE
