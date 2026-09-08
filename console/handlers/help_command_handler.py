from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.help_command import HelpCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.console.help_text import build_help_text
from ai_models_manager.enums.exit_code import ExitCode


class HelpCommandHandler(CommandHandler[HelpCommand]):
    command_type: ClassVar[type[CLICommand]] = HelpCommand

    def __init__(self, console: Console) -> None:
        self.console = console

    def handle(self, command: HelpCommand) -> ExitCode:
        self.console.write("-" * 72, style="separator")
        self.console.write_logo()
        self.console.write("-" * 72, style="separator")
        self.console.write_help(build_help_text().rstrip())
        return ExitCode.SUCCESS
