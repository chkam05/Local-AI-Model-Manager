from typing import ClassVar

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.tool_command import ToolCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.agent.tool_service import ToolService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class ToolCommandHandler(CommandHandler[ToolCommand]):
    command_type: ClassVar[type[CLICommand]] = ToolCommand

    def __init__(self, console: Console, tool_service: ToolService) -> None:
        self.console = console
        self.tool_service = tool_service

    def handle(self, command: ToolCommand) -> ExitCode:
        try:
            tool = self.tool_service.set_enabled(command.tool, command.enabled)
        except ValueError as error:
            raise CLIUsageError(str(error)) from error
        state = "enabled" if command.enabled else "disabled"
        self.console.write(f"OK  Tool {tool} is now {state}.")
        return ExitCode.SUCCESS
