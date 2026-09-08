from enum import Enum


class InstallSourceType(str, Enum):
    AUTO = "auto"
    LORA = "lora"
    MODEL = "model"
