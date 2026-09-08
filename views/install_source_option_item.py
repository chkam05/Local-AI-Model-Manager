from enum import Enum


class InstallSourceOptionItem(str, Enum):
    AUTO = "auto"
    DRAW_THINGS_LORA = "draw-things-lora"
    DRAW_THINGS_MODEL = "draw-things-model"
    OLLAMA = "ollama"
