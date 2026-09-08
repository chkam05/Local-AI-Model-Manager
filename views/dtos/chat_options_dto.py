from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ChatOptionsDto:
    model: str = ""
    context_length: str = ""
    session_name: str = ""
    input_files: str = ""
