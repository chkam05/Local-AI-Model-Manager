from enum import Enum


class DialogButtonAction(Enum):
    """Semantic action represented by a GNU dialog button."""

    ACCEPT = "accept"
    CANCEL = "cancel"
    EXTRA = "extra"
    HELP = "help"
    CONFIRM = "confirm"
    REJECT = "reject"
