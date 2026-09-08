from enum import Enum


class PurgeComponent(str, Enum):
    ALL = "*"
    CODEX = "codex"
    DIALOG = "dialog"
    DRAW_THINGS_CLI = "draw-things-cli"
    DRAW_THINGS_MODELS = "draw-things-models"
    MODELS = "models"
    NPM = "npm"
    OLLAMA = "ollama"
    OLLAMA_MODELS = "ollama-models"
