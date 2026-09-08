import os
from pathlib import Path
import re
import shlex
import subprocess
import time
from typing import Callable, ClassVar, Mapping, Sequence

from ai_models_manager.console.models.process_result import ProcessResult


class ProcessRunner:
    """Run external programs without invoking a command shell."""

    COMMAND_NOT_FOUND: ClassVar[int] = 127
    COMMAND_TIMEOUT: ClassVar[int] = 124
    MAX_STDERR_DIAGNOSTIC: ClassVar[int] = 4000
    SECRET_OPTIONS: ClassVar[frozenset[str]] = frozenset(
        {
            "--api-key",
            "--authorization",
            "--password",
            "--secret",
            "--token",
        }
    )

    def __init__(
        self, debug: Callable[[str], None] | None = None
    ) -> None:
        self._debug = debug

    def run(
        self,
        command: Sequence[str | os.PathLike[str]],
        *,
        capture_output: bool = False,
        capture_stdout: bool = False,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout: float | None = None,
        diagnostics: bool = True,
    ) -> ProcessResult:
        normalized_command = tuple(os.fspath(argument) for argument in command)
        if not normalized_command:
            raise ValueError("Command cannot be empty.")
        if capture_output and capture_stdout:
            raise ValueError(
                "capture_output and capture_stdout cannot both be enabled."
            )

        started_at = time.perf_counter()
        if diagnostics:
            location = f" cwd={cwd}" if cwd is not None else ""
            limit = f" timeout={timeout}s" if timeout is not None else ""
            self.debug(
                f"Executing: {self._format_command(normalized_command)}"
                f"{location}{limit}"
            )

        try:
            completed = subprocess.run(
                normalized_command,
                cwd=cwd,
                env=dict(env) if env is not None else None,
                capture_output=capture_output,
                stdout=(subprocess.PIPE if capture_stdout else None),
                check=False,
                text=True,
                timeout=timeout,
            )
        except FileNotFoundError as error:
            result = ProcessResult(
                command=normalized_command,
                return_code=self.COMMAND_NOT_FOUND,
                stderr=str(error),
            )
            if diagnostics:
                self._write_result_diagnostic(result, started_at)
            return result
        except subprocess.TimeoutExpired as error:
            result = ProcessResult(
                command=normalized_command,
                return_code=self.COMMAND_TIMEOUT,
                stdout=error.stdout or "",
                stderr=error.stderr or "Command timed out.",
            )
            if diagnostics:
                self._write_result_diagnostic(result, started_at)
            return result

        result = ProcessResult(
            command=normalized_command,
            return_code=completed.returncode,
            stdout=completed.stdout or "",
            stderr=completed.stderr or "",
        )
        if diagnostics:
            self._write_result_diagnostic(result, started_at)
        return result

    def debug(self, message: str) -> None:
        if self._debug is not None:
            self._debug(message)

    def _write_result_diagnostic(
        self, result: ProcessResult, started_at: float
    ) -> None:
        elapsed = time.perf_counter() - started_at
        self.debug(
            f"Process exited with code {result.return_code} after "
            f"{elapsed:.3f}s"
        )
        if result.stderr.strip():
            value = self._redact(result.stderr.strip())
            if len(value) > self.MAX_STDERR_DIAGNOSTIC:
                value = value[: self.MAX_STDERR_DIAGNOSTIC] + "… [truncated]"
            self.debug("stderr: " + value.replace("\n", "\nDEBUG stderr: "))

    @classmethod
    def _format_command(cls, command: Sequence[str]) -> str:
        sanitized: list[str] = []
        hide_next = False
        for argument in command:
            if hide_next:
                sanitized.append("[REDACTED]")
                hide_next = False
                continue
            option, separator, _ = argument.partition("=")
            lowered = option.casefold()
            if lowered in cls.SECRET_OPTIONS:
                sanitized.append(
                    f"{option}=[REDACTED]" if separator else option
                )
                hide_next = not separator
                continue
            if lowered == "-h" and argument != "-h":
                sanitized.append(cls._redact(argument))
                continue
            sanitized.append(cls._redact(argument))
        return shlex.join(sanitized)

    @staticmethod
    def _redact(value: str) -> str:
        value = re.sub(
            r"(?i)(authorization:\s*(?:bearer|basic)\s+)\S+",
            r"\1[REDACTED]",
            value,
        )
        value = re.sub(
            r"(?i)((?:x-api-key|api-key|token|secret):\s*)\S+",
            r"\1[REDACTED]",
            value,
        )
        value = re.sub(
            r"(?i)([?&](?:api[_-]?key|token|secret|signature|password)=)[^&\s]+",
            r"\1[REDACTED]",
            value,
        )
        return re.sub(r"(https?://)[^/@\s]+@", r"\1[REDACTED]@", value)

    def start_detached(
        self,
        command: Sequence[str | os.PathLike[str]],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> bool:
        """Start a background process without attaching it to the console."""
        normalized_command = tuple(os.fspath(argument) for argument in command)
        if not normalized_command:
            raise ValueError("Command cannot be empty.")
        self.debug(
            "Starting detached: " + self._format_command(normalized_command)
        )
        try:
            process = subprocess.Popen(
                normalized_command,
                cwd=cwd,
                env=dict(env) if env is not None else None,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except (FileNotFoundError, OSError):
            self.debug("Detached process could not be started.")
            return False
        self.debug(f"Detached process started with PID {process.pid}.")
        return True
