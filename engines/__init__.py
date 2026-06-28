import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_LOCAL_DEPS = os.path.join(_ROOT, ".skill_deps")
if os.path.isdir(_LOCAL_DEPS) and _LOCAL_DEPS not in sys.path:
    sys.path.insert(0, _LOCAL_DEPS)
