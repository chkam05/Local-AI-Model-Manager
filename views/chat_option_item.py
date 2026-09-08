from enum import Enum


class ChatOptionItem(str, Enum):
    MODEL = "model"
    CONTEXT_LENGTH = "context-length"
    SESSION = "session"
    INPUT_FILES = "input-files"
