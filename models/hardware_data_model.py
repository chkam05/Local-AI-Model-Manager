from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HardwareDataModel:
    """Detected hardware used for model ratings and recommendations."""

    system: str
    os_name: str
    architecture: str
    chip: str
    device: str
    ram_gb: float

    @property
    def memory_label(self) -> str:
        return (
            "unified"
            if self.system == "Darwin" and self.architecture == "arm64"
            else "RAM"
        )

