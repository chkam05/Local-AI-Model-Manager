from enum import Enum


class MainMenuItem(str, Enum):
    AGENT = "agent"
    CHAT = "chat"
    EXIT = "exit"
    HELP = "help"
    IMAGE = "image"
    MODELS = "models"
    SYSTEM = "system"
    VERSION = "version"

