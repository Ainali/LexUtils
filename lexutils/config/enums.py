from enum import auto, Enum


class SupportedExampleSources(Enum):
    WIKISOURCE = "Q15156406"
    RIKSDAGEN = "Q21592569"


class Choices(Enum):
    ACCEPT_USAGE_EXAMPLE = auto()
    SKIP_FORM = auto()
    SKIP_USAGE_EXAMPLE = auto()


class LanguageStyle(Enum):
    FORMAL = "Q104597585"
    INFORMAL = "Q901711"


class ReferenceType(Enum):
    WRITTEN = "Q47461344"
    ORAL = "Q52946"


class Result(Enum):
    USAGE_EXAMPLE_ADDED = auto()
    # Todo improve this by using a custom error type instead
    ERROR = auto()