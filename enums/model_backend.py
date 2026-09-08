from enum import Enum


class ModelBackend(str, Enum):
    AUTO = "auto"
    OLLAMA = "ollama"
    DRAW_THINGS = "draw-things"
