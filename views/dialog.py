import os
from pathlib import Path
import shutil
from typing import ClassVar, Mapping, Sequence

from ai_models_manager.config import APP_DISPLAY_NAME, APP_VERSION
from ai_models_manager.console.process_runner import ProcessRunner
from ai_models_manager.views.dtos.dialog_result_dto import DialogResultDto


class Dialog:
    """Execute dialog widgets with application-wide terminal options."""

    EXECUTABLE: ClassVar[str] = "dialog"
    OPTION_BACKTITLE: ClassVar[str] = "--backtitle"
    OPTION_COLORS: ClassVar[str] = "--colors"
    OPTION_CURSOR_OFF_LABEL: ClassVar[str] = "--cursor-off-label"
    OPTION_NO_COLLAPSE: ClassVar[str] = "--no-collapse"
    OPTION_STDOUT: ClassVar[str] = "--stdout"
    ENV_DIALOGRC: ClassVar[str] = "DIALOGRC"
    THEME_FILE: ClassVar[Path] = Path(__file__).with_name("dialogrc")
    MODEL_BROWSER_THEME_FILE: ClassVar[Path] = Path(__file__).with_name(
        "dialog-models.rc"
    )
    MODEL_SORT_THEME_FILE: ClassVar[Path] = Path(__file__).with_name(
        "dialog-model-sort.rc"
    )

    def __init__(self, process_runner: ProcessRunner) -> None:
        self.process_runner = process_runner

    def is_available(self) -> bool:
        return shutil.which(self.EXECUTABLE) is not None

    def render(
        self,
        arguments: Sequence[str],
        *,
        capture_output: bool = False,
        env: Mapping[str, str] | None = None,
    ) -> DialogResultDto:
        command = [self.EXECUTABLE]
        if capture_output:
            command.append(self.OPTION_STDOUT)
        command.extend(
            (
                self.OPTION_BACKTITLE,
                f"{APP_DISPLAY_NAME} v{APP_VERSION}",
                self.OPTION_COLORS,
                self.OPTION_CURSOR_OFF_LABEL,
                self.OPTION_NO_COLLAPSE,
                *arguments,
            )
        )
        process_environment = {
            **os.environ,
            self.ENV_DIALOGRC: str(self.THEME_FILE),
        }
        if env is not None:
            process_environment.update(env)
        result = self.process_runner.run(
            command,
            capture_stdout=capture_output,
            env=process_environment,
            diagnostics=False,
        )
        return DialogResultDto(
            exit_code=result.return_code,
            output=result.stdout.rstrip("\r\n"),
        )

    def clear(self) -> DialogResultDto:
        return self.render(("--clear",))

    def render_with_environment(
        self,
        arguments: Sequence[str],
        environment: Mapping[str, str],
        *,
        capture_output: bool = False,
    ) -> DialogResultDto:
        return self.render(
            arguments,
            capture_output=capture_output,
            env=environment,
        )
