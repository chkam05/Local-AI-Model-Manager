from pathlib import Path
from typing import ClassVar, Sequence

from ai_models_manager.console.commands.cli_command import CLICommand
from ai_models_manager.console.commands.image_command import ImageCommand
from ai_models_manager.console.console import Console
from ai_models_manager.console.handlers.command_handler import CommandHandler
from ai_models_manager.core.image_service import ImageService
from ai_models_manager.enums.exit_code import ExitCode
from ai_models_manager.exceptions.cli_error import CLIError
from ai_models_manager.exceptions.ollama_backend_error import OllamaBackendError


class ImageCommandHandler(CommandHandler[ImageCommand]):
    command_type: ClassVar[type[CLICommand]] = ImageCommand

    def __init__(self, console: Console, image_service: ImageService) -> None:
        self.console = console
        self.image_service = image_service

    def handle(self, command: ImageCommand) -> ExitCode:
        return self.generate_image(
            command.model,
            command.width,
            command.height,
            command.output_directory,
            command.file_name,
            command.prompt,
            command.input_files,
            command.strength,
        )

    def generate_image(
        self,
        model: str | None,
        width: int,
        height: int,
        output_directory: Path | None,
        file_name: str | None,
        prompt: str,
        input_files: Sequence[Path],
        strength: float | None,
    ) -> ExitCode:
        try:
            result = self.image_service.generate(
                model=model,
                width=width,
                height=height,
                output_directory=output_directory,
                file_name=file_name,
                prompt=prompt,
                input_files=input_files,
                strength=strength,
                warning=self.console.warning,
                started=self._write_generation_details,
            )
        except (
            FileNotFoundError,
            OllamaBackendError,
            OSError,
            RuntimeError,
            ValueError,
        ) as error:
            raise CLIError(str(error), ExitCode.ERROR) from error
        self.console.write(
            f"OK  Image saved: {result.output_path} "
            f"[{result.backend}, {result.model}, "
            f"{result.width}x{result.height}]"
        )
        return ExitCode.SUCCESS

    def _write_generation_details(
        self,
        model: str,
        output_path: Path,
        width: int,
        height: int,
        prompt: str,
        input_files: tuple[Path, ...],
        strength: float | None,
    ) -> None:
        separator = "-" * 80
        label_width = len("Input Files")
        prompt_lines = prompt.splitlines() or [""]
        self.console.write(separator, style="separator")
        self._write_detail("Model", model, label_width)
        self._write_detail("File Path", str(output_path), label_width)
        self._write_detail("Size", f"{width}x{height}", label_width)
        self._write_detail("Prompt", prompt_lines[0], label_width)
        for line in prompt_lines[1:]:
            self.console.write(f"{'':<{label_width + 2}}{line}")
        if input_files:
            self._write_detail(
                "Input Files", str(input_files[0]), label_width
            )
            for input_file in input_files[1:]:
                self.console.write(
                    f"{'':<{label_width + 2}}{input_file}"
                )
            self._write_detail(
                "Strength", f"{strength:.2f}", label_width
            )
        else:
            self._write_detail("Input Files", "-", label_width)
        self.console.write(separator, style="separator")
        self.console.blank_line()
        self.console.write("Generating image...")

    def _write_detail(self, label: str, value: str, width: int) -> None:
        self.console.write(f"{label + ':':<{width + 1}} {value}")
