import argparse
from typing import NoReturn

from ai_models_manager.exceptions.cli_usage_error import CLIUsageError


class _ArgumentParser(argparse.ArgumentParser):
    """ArgumentParser which reports errors instead of exiting the process."""

    def error(self, message: str) -> NoReturn:
        raise CLIUsageError(message)
