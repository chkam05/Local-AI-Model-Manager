import re
from typing import Callable, ClassVar, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.version_command import VersionCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.version_service import VersionService
from ai_models_manager.enums.exit_code import ExitCode


class VersionCommandHandler(CommandHandler[VersionCommand]):
    command_type: ClassVar[type[CLICommand]] = VersionCommand

    def __init__(self, console: Console, version_service: VersionService) -> None:
        self.console = console
        self.version_service = version_service

    def handle(self, command: VersionCommand) -> ExitCode:
        self.console.write("-" * 72, style="separator")
        self.console.write_logo()
        self.console.write("-" * 72, style="separator")
        self._print_table(
            ("Component", "Version", "Update", "Size"),
            tuple(
                (row.component, row.version, row.update, row.size)
                for row in self.version_service.components()
            ),
        )
        self.console.write("")
        self._print_table(
            ("Component", "Size"),
            tuple(
                (row.component, row.size)
                for row in self.version_service.model_storage()
            ),
        )
        return ExitCode.SUCCESS

    def _print_table(
        self,
        headers: Sequence[str],
        rows: Sequence[Sequence[str]],
    ) -> None:
        widths = tuple(
            max(len(headers[index]), *(len(row[index]) for row in rows))
            for index in range(len(headers))
        )
        self.console.write(self._format_row(headers, widths), style="heading")
        self.console.write(self._format_separator(widths), style="separator")
        size_index = headers.index("Size") if "Size" in headers else None
        sizes = (
            tuple(self._size_bytes(row[size_index]) for row in rows)
            if size_index is not None
            else ()
        )
        positive_sizes = tuple(size for size in sizes if size > 0)
        minimum = min(positive_sizes, default=0)
        maximum = max(positive_sizes, default=0)
        for row in rows:
            colorizers: dict[int, Callable[[str], str]] = {}
            for index, header in enumerate(headers):
                if header == "Update" and row[index] != "-":
                    colorizers[index] = self.console.colors.update
                elif header == "Size":
                    size = self._size_bytes(row[index])
                    colorizers[index] = (
                        lambda text,
                        value=size: self.console.colors.size_scale(
                            text, value, minimum, maximum
                        )
                    )
            values = tuple(
                colorizers[index](f"{value:<{widths[index]}}")
                if index in colorizers
                else f"{value:<{widths[index]}}"
                for index, value in enumerate(row)
            )
            self.console.write("  ".join(values).rstrip())

    @staticmethod
    def _format_row(row: Sequence[str], widths: Sequence[int]) -> str:
        return "  ".join(
            f"{value:<{widths[index]}}" for index, value in enumerate(row)
        ).rstrip()

    @staticmethod
    def _format_separator(widths: Sequence[int]) -> str:
        return "  ".join("-" * width for width in widths)

    @staticmethod
    def _size_bytes(value: str) -> int:
        match = re.fullmatch(r"([0-9]+(?:[.,][0-9]+)?)\s*([KMGT]?B)", value)
        if match is None:
            return 0
        multipliers = {
            "B": 1,
            "KB": 1000,
            "MB": 1000**2,
            "GB": 1000**3,
            "TB": 1000**4,
        }
        return int(
            float(match.group(1).replace(",", "."))
            * multipliers[match.group(2)]
        )
