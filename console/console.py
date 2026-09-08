from pathlib import Path
import re
import sys
import termios
import tty
from typing import TextIO

from ai_models_manager.console.console_colors import ConsoleColors


class Console:
    """Text streams used by command-line commands."""

    def __init__(
        self,
        stdin: TextIO = sys.stdin,
        stdout: TextIO = sys.stdout,
        stderr: TextIO = sys.stderr,
        verbose: bool = False,
    ) -> None:
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr
        self.verbose = verbose
        self.colors = ConsoleColors.for_stream(stdout)
        self.error_colors = ConsoleColors.for_stream(stderr)

    def read(self, prompt: str = "") -> str | None:
        if prompt:
            self.stdout.write(prompt)
            self.stdout.flush()
        value = self.stdin.readline()
        return None if value == "" else value.rstrip("\r\n")

    def confirm(self, prompt: str = "Continue? [y/N]: ") -> bool:
        """Accept an operation only when the user explicitly enters y."""
        answer = self.read(prompt)
        return answer is not None and answer.strip().casefold() == "y"

    def wait_for_key(self, prompt: str = "Press any key to continue...") -> None:
        """Wait for one key on an interactive terminal, with a stream fallback."""
        self.stdout.write(prompt)
        self.stdout.flush()
        try:
            file_descriptor = self.stdin.fileno()
            if self.stdin.isatty():
                previous = termios.tcgetattr(file_descriptor)
                try:
                    tty.setcbreak(file_descriptor)
                    self.stdin.read(1)
                finally:
                    termios.tcsetattr(file_descriptor, termios.TCSADRAIN, previous)
                self.stdout.write("\n")
                self.stdout.flush()
                return
        except (AttributeError, OSError, termios.error):
            pass
        self.stdin.readline()

    def write(self, message: str, *, style: str | None = None) -> None:
        if style == "heading":
            message = self.colors.heading(message)
        elif style == "separator":
            message = self.colors.separator(message)
        elif style == "success":
            message = self.colors.success(message)
        elif message.startswith("OK  "):
            message = self.colors.success("OK") + message[2:]
        print(message, file=self.stdout, flush=True)

    def error(self, message: str) -> None:
        print(
            self.error_colors.error("ERR") + f" {message}",
            file=self.stderr,
            flush=True,
        )

    def warning(self, message: str) -> None:
        print(
            self.error_colors.warning("WARN") + f" {message}",
            file=self.stderr,
            flush=True,
        )

    def debug(self, message: str) -> None:
        if not self.verbose:
            return
        print(
            self.error_colors.apply(
                "DEBUG", self.error_colors.BOLD, self.error_colors.MAGENTA
            )
            + f" {message}",
            file=self.stderr,
            flush=True,
        )

    def blank_line(self) -> None:
        print(file=self.stdout, flush=True)

    def clear_screen(self) -> None:
        """Clear the terminal and place the cursor in its top-left corner."""
        self.stdout.write("\r\033[2J\033[H")
        self.stdout.flush()

    def restore_terminal_mode(self) -> None:
        """Restore the cooked TTY flags needed by interactive CLI programs."""
        try:
            file_descriptor = self.stdin.fileno()
            if not self.stdin.isatty():
                return
            attributes = termios.tcgetattr(file_descriptor)
            attributes[0] |= termios.BRKINT | termios.ICRNL | termios.IXON
            attributes[1] |= termios.OPOST | termios.ONLCR
            attributes[2] |= termios.CREAD
            attributes[3] |= (
                termios.ECHO
                | termios.ECHONL
                | termios.ICANON
                | termios.IEXTEN
                | termios.ISIG
            )
            termios.tcsetattr(file_descriptor, termios.TCSANOW, attributes)
        except (AttributeError, OSError, termios.error):
            return

    def discard_pending_input(self) -> None:
        """Discard keys typed before the next interactive prompt."""
        try:
            file_descriptor = self.stdin.fileno()
            if self.stdin.isatty():
                termios.tcflush(file_descriptor, termios.TCIFLUSH)
        except (AttributeError, OSError, termios.error):
            return

    def generate_logo(self) -> str:
        logo_path = Path(__file__).with_name("logo.txt")
        return logo_path.read_text(encoding="utf-8").rstrip("\n")

    def write_logo(self) -> None:
        logo = self.generate_logo()
        self.write(self.colors.apply(logo, self.colors.BOLD, self.colors.RED))

    def write_help(self, text: str) -> None:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.endswith(":") and not stripped.startswith("ai "):
                self.write(self.colors.heading(line))
                continue
            colored = re.sub(
                r"(?<![\w-])(--[a-z0-9-]+|-[a-zA-Z])(?![\w-])",
                lambda match: self.colors.switch(match.group(0)),
                line,
            )
            colored = re.sub(
                r"(?<![\w])ai(?=\s|$)",
                lambda match: self.colors.command(match.group(0)),
                colored,
            )
            colored = re.sub(
                r"\b(MODEL|SESSION|NAME|FILE|DIR|VALUE|FIELD|TARGET|"
                r"TOOL|COMPONENT|SOURCE|PROMPT|NEW_NAME|PX)\b",
                lambda match: self.colors.value(match.group(0)),
                colored,
            )
            self.write(colored)

    def write_inline(self, message: str) -> None:
        self.stdout.write(message)
        self.stdout.flush()

    def finish_line(self) -> None:
        self.stdout.write("\n")
        self.stdout.flush()
