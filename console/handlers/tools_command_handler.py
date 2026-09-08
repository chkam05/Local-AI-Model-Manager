from typing import ClassVar, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.tools_command import ToolsCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.agent.tool_service import ToolService
from ai_models_manager.core.storage.tool_settings_storage import ToolSettingsStorage
from ai_models_manager.enums.exit_code import ExitCode


class ToolsCommandHandler(CommandHandler[ToolsCommand]):
    command_type: ClassVar[type[CLICommand]] = ToolsCommand

    def __init__(
        self,
        console: Console,
        tool_service: ToolService,
        tool_settings_storage: ToolSettingsStorage,
    ) -> None:
        self.console = console
        self.tool_service = tool_service
        self.tool_settings_storage = tool_settings_storage

    def handle(self, command: ToolsCommand) -> ExitCode:
        headers = ("Tool", "State", "Scope", "Description")
        rows = tuple(
            (
                definition.name,
                "Enabled" if enabled else "Disabled",
                definition.scope,
                definition.description,
            )
            for definition, enabled in self.tool_service.definitions()
        )
        widths = tuple(
            max(len(headers[index]), *(len(row[index]) for row in rows))
            for index in range(len(headers))
        )
        self.console.write(self._format_row(headers, widths), style="heading")
        self.console.write(self._format_separator(widths), style="separator")
        for row in rows:
            self.console.write(self._format_row(row, widths))
        self.console.write(
            f"\nConfiguration: {self.tool_settings_storage.file_path}"
        )
        return ExitCode.SUCCESS

    @staticmethod
    def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
        return "  ".join(
            f"{value:<{widths[index]}}" for index, value in enumerate(row)
        ).rstrip()

    @staticmethod
    def _format_separator(widths: Sequence[int]) -> str:
        return "  ".join("-" * width for width in widths)
