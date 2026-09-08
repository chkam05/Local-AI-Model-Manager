from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True, slots=True)
class OllamaModel:
    """A locally installed Ollama model."""

    name: str
    model_id: str
    size: str
    modified: str

    SIZE_MULTIPLIERS: ClassVar[dict[str, int]] = {
        "B": 1,
        "KB": 1024,
        "KIB": 1024,
        "MB": 1024**2,
        "MIB": 1024**2,
        "GB": 1024**3,
        "GIB": 1024**3,
        "TB": 1024**4,
        "TIB": 1024**4,
    }

    @property
    def size_bytes(self) -> int:
        parts = self.size.replace(",", ".").split()
        if len(parts) != 2:
            return 0
        try:
            value = float(parts[0])
        except ValueError:
            return 0
        multiplier = self.SIZE_MULTIPLIERS.get(parts[1].upper(), 0)
        return int(value * multiplier)
