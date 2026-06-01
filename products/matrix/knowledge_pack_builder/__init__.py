"""Import shim for the Matrix knowledge pack builder package."""

from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "knowledge-pack-builder" / "src"
__path__.append(str(_SRC))

