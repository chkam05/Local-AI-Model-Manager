from io import StringIO
from typing import Callable

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.console_colors import ConsoleColors
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.views.dtos.tui_command_result_dto import (
    TUICommandResultDto,
)


class TUICommandExecutor:
    """Execute a registered CLI command and capture plain text for dialog."""

    def __init__(
        self,
        console: Console,
        execute: Callable[[CLICommand], ExitCode],
    ) -> None:
        self.console = console
        self.execute = execute

    def run(self, command: CLICommand) -> TUICommandResultDto:
        stdout = StringIO()
        stderr = StringIO()
        original_stdout = self.console.stdout
        original_stderr = self.console.stderr
        original_colors = self.console.colors
        original_error_colors = self.console.error_colors
        self.console.stdout = stdout
        self.console.stderr = stderr
        self.console.colors = ConsoleColors(enabled=False)
        self.console.error_colors = ConsoleColors(enabled=False)
        try:
            try:
                exit_code = self.execute(command)
            except CLIError as error:
                exit_code = error.exit_code
                self.console.error(str(error))
            output = "\n".join(
                part.strip()
                for part in (stdout.getvalue(), stderr.getvalue())
                if part.strip()
            )
            return TUICommandResultDto(
                exit_code=exit_code,
                output=output or "Operation completed.",
            )
        finally:
            self.console.stdout = original_stdout
            self.console.stderr = original_stderr
            self.console.colors = original_colors
            self.console.error_colors = original_error_colors

    def run_interactive(self, command: CLICommand) -> TUICommandResultDto:
        """Execute a command directly in the terminal without capturing I/O."""
        try:
            exit_code = self.execute(command)
        except CLIError as error:
            self.console.error(str(error))
            return TUICommandResultDto(error.exit_code, str(error))
        return TUICommandResultDto(exit_code, "Operation completed.")
