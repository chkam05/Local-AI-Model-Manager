from enum import Enum


class ImageOptionItem(str, Enum):
    MODEL = "model"
    WIDTH = "width"
    HEIGHT = "height"
    DIRECTORY = "directory"
    FILE_NAME = "file-name"
    INPUT_FILES = "input-files"
    STRENGTH = "strength"
