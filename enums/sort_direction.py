from enum import Enum


class SortDirection(str, Enum):
    AUTO = "auto"
    ASCENDING = "asc"
    DESCENDING = "desc"
