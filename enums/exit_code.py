from enum import Enum


class ExitCode(int, Enum):
    SUCCESS = 0
    ERROR = 1
    USAGE_ERROR = 2
    NOT_IMPLEMENTED = 3
