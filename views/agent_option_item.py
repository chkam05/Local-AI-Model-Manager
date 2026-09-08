from enum import Enum


class AgentOptionItem(str, Enum):
    MODEL = "model"
    DIRECTORY = "directory"
    CONTEXT_LENGTH = "context-length"
    SESSION = "session"
    EXECUTION = "execution"
    INPUT_FILES = "input-files"
    TOOLS = "tools"
