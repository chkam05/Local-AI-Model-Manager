from enum import Enum


class InstallModelsMenuItem(str, Enum):
    DRAW_THINGS = "draw-things"
    OLLAMA = "ollama"
    OLLAMA_EXPERIMENTAL = "ollama-experimental"
    FILE = "file"
    URL = "url"
