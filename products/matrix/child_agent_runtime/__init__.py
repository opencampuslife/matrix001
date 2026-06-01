"""Import shim for the Matrix child agent runtime package.

The implementation lives under ``child-agent-runtime/src`` to preserve the
USB product layout. Extending ``__path__`` keeps ``python -m pytest`` and
``python -m child_agent_runtime`` working from ``products/matrix`` without
copying the runtime modules.
"""

from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "child-agent-runtime" / "src"
__path__.append(str(_SRC))

