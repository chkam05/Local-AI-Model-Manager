from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class DiskSpaceCheck:
    available_bytes: int
    destination: Path
    required_bytes: int
    reserve_bytes: int

    @property
    def total_required_bytes(self) -> int:
        return self.required_bytes + self.reserve_bytes

    @property
    def sufficient(self) -> bool:
        return self.available_bytes >= self.total_required_bytes
