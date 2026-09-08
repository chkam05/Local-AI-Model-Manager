from enum import Enum


class ModelOptionItem(str, Enum):
    AGENT = "agent"
    CHAT = "chat"
    DETAILS = "details"
    IMAGE = "image"
    RUN = "run"
    SET_BASE = "set-base"
    STOP = "stop"
    UNINSTALL = "uninstall"
    UPDATE = "update"
