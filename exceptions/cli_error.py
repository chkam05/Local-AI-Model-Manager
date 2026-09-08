from ai_models_manager.enums.exit_code import ExitCode


class CLIError(Exception):
    """An error that can be presented directly to a command-line user."""

    def __init__(self, message: str, exit_code: ExitCode) -> None:
        super().__init__(message)
        self.exit_code = exit_code
