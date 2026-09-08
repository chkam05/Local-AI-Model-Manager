import os
from typing import ClassVar, TextIO


class ConsoleColors:
    """ANSI color definitions and semantic console styles."""

    RESET: ClassVar[str] = "\033[0m"
    BOLD: ClassVar[str] = "\033[1m"
    DIM: ClassVar[str] = "\033[2m"
    ITALIC: ClassVar[str] = "\033[3m"
    UNDERLINE: ClassVar[str] = "\033[4m"
    REVERSE: ClassVar[str] = "\033[7m"

    BLACK: ClassVar[str] = "\033[30m"
    RED: ClassVar[str] = "\033[31m"
    GREEN: ClassVar[str] = "\033[32m"
    YELLOW: ClassVar[str] = "\033[33m"
    BLUE: ClassVar[str] = "\033[34m"
    MAGENTA: ClassVar[str] = "\033[35m"
    CYAN: ClassVar[str] = "\033[36m"
    WHITE: ClassVar[str] = "\033[37m"

    BRIGHT_BLACK: ClassVar[str] = "\033[90m"
    BRIGHT_RED: ClassVar[str] = "\033[91m"
    BRIGHT_GREEN: ClassVar[str] = "\033[92m"
    BRIGHT_YELLOW: ClassVar[str] = "\033[93m"
    BRIGHT_BLUE: ClassVar[str] = "\033[94m"
    BRIGHT_MAGENTA: ClassVar[str] = "\033[95m"
    BRIGHT_CYAN: ClassVar[str] = "\033[96m"
    BRIGHT_WHITE: ClassVar[str] = "\033[97m"
    ORANGE: ClassVar[str] = "\033[38;5;208m"

    BG_BLACK: ClassVar[str] = "\033[40m"
    BG_RED: ClassVar[str] = "\033[41m"
    BG_GREEN: ClassVar[str] = "\033[42m"
    BG_YELLOW: ClassVar[str] = "\033[43m"
    BG_BLUE: ClassVar[str] = "\033[44m"
    BG_MAGENTA: ClassVar[str] = "\033[45m"
    BG_CYAN: ClassVar[str] = "\033[46m"
    BG_WHITE: ClassVar[str] = "\033[47m"

    BG_BRIGHT_BLACK: ClassVar[str] = "\033[100m"
    BG_BRIGHT_RED: ClassVar[str] = "\033[101m"
    BG_BRIGHT_GREEN: ClassVar[str] = "\033[102m"
    BG_BRIGHT_YELLOW: ClassVar[str] = "\033[103m"
    BG_BRIGHT_BLUE: ClassVar[str] = "\033[104m"
    BG_BRIGHT_MAGENTA: ClassVar[str] = "\033[105m"
    BG_BRIGHT_CYAN: ClassVar[str] = "\033[106m"
    BG_BRIGHT_WHITE: ClassVar[str] = "\033[107m"

    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled

    @classmethod
    def for_stream(cls, stream: TextIO) -> "ConsoleColors":
        enabled = (
            bool(getattr(stream, "isatty", lambda: False)())
            and "NO_COLOR" not in os.environ
            and os.environ.get("TERM", "") != "dumb"
        )
        return cls(enabled)

    def apply(self, text: str, *styles: str) -> str:
        if not self.enabled or not text:
            return text
        return "".join(styles) + text + self.RESET

    def error(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.RED)

    def success(self, text: str) -> str:
        return self.apply(text, self.GREEN)

    def warning(self, text: str) -> str:
        return self.apply(text, self.YELLOW)

    def heading(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.BRIGHT_YELLOW)

    def command(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.GREEN)

    def switch(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.MAGENTA)

    def value(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.CYAN)

    def separator(self, text: str) -> str:
        return self.apply(text, self.DIM, self.BRIGHT_BLACK)

    def update(self, text: str) -> str:
        return self.apply(text, self.BOLD, self.BRIGHT_GREEN)

    def rating(self, text: str) -> str:
        try:
            value = float(text.strip().removesuffix("%"))
        except ValueError:
            return self.apply(text, self.DIM, self.WHITE)
        if value <= 0:
            return self.apply(text, self.DIM, self.BRIGHT_BLACK)
        if value >= 80:
            return self.apply(text, self.BRIGHT_GREEN)
        if value >= 60:
            return self.apply(text, self.BRIGHT_YELLOW)
        if value >= 40:
            return self.apply(text, self.ORANGE)
        return self.apply(text, self.BRIGHT_RED)

    def size_scale(
        self,
        text: str,
        value: int,
        minimum: int,
        maximum: int,
    ) -> str:
        """Color a size relative to the positive values in its current table."""
        if value <= 0:
            return self.apply(text, self.DIM, self.BRIGHT_BLACK)
        if maximum <= minimum:
            return self.apply(text, self.BRIGHT_WHITE)
        position = (value - minimum) / (maximum - minimum)
        if position <= 0.25:
            return self.apply(text, self.BRIGHT_WHITE)
        if position <= 0.50:
            return self.apply(text, self.BRIGHT_YELLOW)
        if position <= 0.75:
            return self.apply(text, self.ORANGE)
        return self.apply(text, self.BRIGHT_RED)

    def state(self, text: str) -> str:
        if text.casefold() == "running":
            return self.apply(text, self.BOLD, self.BRIGHT_GREEN)
        if text.casefold() == "stopped":
            return self.apply(text, self.YELLOW)
        return self.apply(text, self.DIM, self.WHITE)
