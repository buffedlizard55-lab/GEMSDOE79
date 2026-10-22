from __future__ import annotations

from pathlib import Path
import sys
import warnings

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _extra in (ROOT / "src", ROOT / "vendor", ROOT / "scripts"):
    _s = str(_extra)
    if _s not in sys.path:
        sys.path.insert(0, _s)


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config: pytest.Config) -> None:
    """Silence upstream rasterio 1.5 internal transform PendingDeprecationWarning while keeping project warnings visible."""
    warnings.filterwarnings(
        "ignore",
        message=r".*from_origin.*",
        category=PendingDeprecationWarning,
        module=r"rasterio(\..*)?$",
    )
    warnings.filterwarnings(
        "ignore",
        message=r"Use `@` matmul instead of `\*` mul operator.*",
        category=PendingDeprecationWarning,
        module=r"rasterio(\..*)?$",
    )
