from enum import Enum


class SystemMenuItem(str, Enum):
    PURGE = "purge"
    SETUP = "setup"
    TOOLS = "tools"
    UPDATE = "update"
