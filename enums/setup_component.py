from enum import Enum


class SetupComponent(str, Enum):
    CODEX = "codex"
    DIALOG = "dialog"
    DRAW_THINGS_CLI = "draw-things-cli"
    IMAGEMAGICK = "imagemagick"
    NPM = "npm"
    OLLAMA = "ollama"
