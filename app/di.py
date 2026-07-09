"""Framework primitives shared across layers.

Re-exports FastAPI's ``Request`` so the pure-domain ``UserManager`` hooks can
type their optional ``request`` argument without a *direct* ``fastapi``/
``starlette`` import (which the import-linter domain contract forbids). Reaching
it through this module is an indirect import, which the contract explicitly
allows. This module is not part of the layer stack, so no contract governs it.
"""

from fastapi import Request

__all__ = ["Request"]
