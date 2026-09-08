from typing import ClassVar
import re


class DialogColors:
    """GNU dialog color escapes corresponding to console help styles."""

    RESET: ClassVar[str] = r"\Zn"
    BOLD: ClassVar[str] = r"\Zb"
    BLACK: ClassVar[str] = r"\Z0"
    RED: ClassVar[str] = r"\Z1"
    GREEN: ClassVar[str] = r"\Z2"
    YELLOW: ClassVar[str] = r"\Z3"
    MAGENTA: ClassVar[str] = r"\Z5"
    CYAN: ClassVar[str] = r"\Z6"

    @classmethod
    def apply(cls, text: str, *styles: str) -> str:
        return "".join(styles) + text + cls.RESET

    @classmethod
    def command(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.GREEN)

    @classmethod
    def heading(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.YELLOW)

    @classmethod
    def logo(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.RED)

    @classmethod
    def separator(cls, text: str) -> str:
        return cls.apply(text, cls.BLACK)

    @classmethod
    def switch(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.MAGENTA)

    @classmethod
    def value(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.CYAN)

    @classmethod
    def version(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.CYAN)

    @classmethod
    def update(cls, text: str) -> str:
        return cls.apply(text, cls.BOLD, cls.GREEN)

    @classmethod
    def rating(cls, text: str) -> str:
        try:
            value = float(text.strip().removesuffix("%"))
        except ValueError:
            return cls.apply(text, cls.BLACK)
        if value <= 0:
            return cls.apply(text, cls.BLACK)
        if value >= 80:
            return cls.apply(text, cls.BOLD, cls.GREEN)
        if value >= 60:
            return cls.apply(text, cls.BOLD, cls.YELLOW)
        if value >= 40:
            return cls.apply(text, cls.BOLD, cls.MAGENTA)
        return cls.apply(text, cls.BOLD, cls.RED)

    @classmethod
    def size_scale(
        cls,
        text: str,
        value: int,
        minimum: int,
        maximum: int,
    ) -> str:
        if value <= 0:
            return cls.apply(text, cls.BLACK)
        if maximum <= minimum:
            return cls.apply(text, cls.BOLD)
        position = (value - minimum) / (maximum - minimum)
        if position <= 0.25:
            return cls.apply(text, cls.BOLD)
        if position <= 0.50:
            return cls.apply(text, cls.BOLD, cls.YELLOW)
        if position <= 0.75:
            return cls.apply(text, cls.BOLD, cls.MAGENTA)
        return cls.apply(text, cls.BOLD, cls.RED)

    @staticmethod
    def size_bytes(value: str) -> int:
        match = re.fullmatch(
            r"([0-9]+(?:[.,][0-9]+)?)\s*([KMGT]?B)", value.strip()
        )
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
