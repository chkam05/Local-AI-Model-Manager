from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError


class CLIUsageError(CLIError):
    def __init__(self, message: str) -> None:
        super().__init__(message, ExitCode.USAGE_ERROR)
