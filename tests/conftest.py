"""Shared pytest setup."""

import sys
from unittest.mock import MagicMock

try:
    import onnxruntime  # noqa: F401
except ImportError:
    # CI installs only `.[dev]`; MusiCNN unit tests patch onnxruntime.
    sys.modules.setdefault("onnxruntime", MagicMock())
