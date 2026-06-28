from .no_memory import NoMemory
from .naive_markdown import NaiveMarkdown

REGISTRY = {
    "no_memory": NoMemory,
    "naive_markdown": NaiveMarkdown,
}

try:
    from .mem0_system import Mem0System
    REGISTRY["mem0"] = Mem0System
except ImportError:
    pass
