from enum import Enum


class ListTarget(str, Enum):
    DRAW_THINGS = "draw-things"
    LOCAL = "local"
    OLLAMA = "ollama"
    OLLAMA_EXPERIMENTAL = "ollama-experimental"
