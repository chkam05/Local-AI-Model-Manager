from enum import Enum


class InputFileType(str, Enum):
    IMAGE = "image"
    TEXT = "text"
    UNSUPPORTED = "unsupported"
