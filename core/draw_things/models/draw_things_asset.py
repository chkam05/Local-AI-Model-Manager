from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DrawThingsAsset:
    """Draw Things model or supporting local asset."""

    file_name: str
    display_name: str
    size_bytes: int
    source: str = ""
    note: str = ""
    asset_type: str = "Model"
    dependencies: tuple[str, ...] = ()
