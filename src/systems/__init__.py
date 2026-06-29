from .no_memory import NoMemory
from .naive_markdown import NaiveMarkdown
from .long_context import LongContext
from .regex_markdown import RegexMarkdown

REGISTRY = {
    "no_memory": NoMemory,
    "naive_markdown": NaiveMarkdown,
    "long_context": LongContext,
    "regex_markdown": RegexMarkdown,
}

try:
    from .mem0_system import Mem0System
    REGISTRY["mem0"] = Mem0System
except ImportError:
    pass
