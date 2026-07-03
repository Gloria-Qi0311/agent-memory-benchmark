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

try:
    from .pure_vector import PureVector
    REGISTRY["pure_vector"] = PureVector
except ImportError:
    pass

try:
    from .amh_system import AMHSystem
    REGISTRY["amh"] = AMHSystem
except ImportError:
    pass
