from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SystemConfirmationDto:
    title: str
    message: str
    confirm_label: str
