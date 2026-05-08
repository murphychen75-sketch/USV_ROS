"""
Runtime compatibility patches for third-party ROS Python dependencies.

This module is auto-imported by Python (via `site`) when it is available on
sys.path. We only provide small shims needed by older transforms3d versions
under NumPy >= 2.0.
"""

from __future__ import annotations

import numpy as np


if not hasattr(np, "float"):
    # Backward compatibility for legacy libraries that still reference np.float.
    np.float = float  # type: ignore[attr-defined]


if not hasattr(np, "maximum_sctype"):
    def _maximum_sctype(dtype_like):
        """Minimal replacement for removed numpy.maximum_sctype (NumPy 2.x)."""
        kind = np.dtype(dtype_like).kind
        if kind == "f":
            return np.float64
        if kind == "c":
            return np.complex128
        if kind in ("i", "u"):
            return np.int64 if kind == "i" else np.uint64
        if kind == "b":
            return np.bool_
        return np.dtype(dtype_like).type

    np.maximum_sctype = _maximum_sctype  # type: ignore[attr-defined]
