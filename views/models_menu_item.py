from enum import Enum


class ModelsMenuItem(str, Enum):
    DEPENDENCIES = "dependencies"
    INSTALL = "install"
    LOCAL = "local"
    REFRESH = "refresh"
