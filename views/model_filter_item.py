from enum import Enum


class ModelFilterItem(str, Enum):
    NAME = "name"
    BACKEND = "backend"
    TYPE = "asset_type"
    STATE = "state"
    CATEGORY = "category"
