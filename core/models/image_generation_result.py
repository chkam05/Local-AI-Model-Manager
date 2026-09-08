from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ImageGenerationResult:
    backend: str
    height: int
    model: str
    output_path: Path
    width: int
