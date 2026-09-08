from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ImageOptionsDto:
    model: str = ""
    prompt: str = ""
    width: str = "800"
    height: str = "600"
    output_directory: str = ""
    file_name: str = ""
    input_files: str = ""
    strength: str = ""
