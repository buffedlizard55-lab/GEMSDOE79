from __future__ import annotations

import warnings

import pytest


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
