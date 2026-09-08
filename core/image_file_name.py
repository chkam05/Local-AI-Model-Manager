from datetime import datetime
from pathlib import Path
import re


def automatic_image_file_name(
    model: str | None,
    moment: datetime | None = None,
) -> str:
    """Build the default PNG name shown by the TUI and used by generation."""
    raw_name = Path(model or "image").name
    model_name = Path(raw_name).stem or "image"
    safe_model_name = re.sub(r"[^A-Za-z0-9._-]+", "_", model_name).strip("._-")
    timestamp = (moment or datetime.now()).strftime("%Y%m%d%H%M%f")[:15]
    return f"{safe_model_name or 'image'}_{timestamp}.png"
