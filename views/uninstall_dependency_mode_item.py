from enum import Enum


class UninstallDependencyModeItem(str, Enum):
    ALL = "all"
    KEEP = "keep"
    UNUSED = "unused"
