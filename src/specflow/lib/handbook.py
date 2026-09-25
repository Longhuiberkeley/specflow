"""Deprecated compatibility facade for the bundled practice seed catalogue.

The canonical implementation now lives in :mod:`specflow.lib.practices_seed`.
This module remains import-compatible for existing callers.
"""

from specflow.lib.practices_seed import (
    DOMAIN_PRACTICES,
    GENERIC_PRACTICES,
    SEED_PRACTICES,
    Practice,
    format_handbook_text,
    generate_handbook,
    get_practices,
    get_seed_practices,
)

__all__ = [
    "DOMAIN_PRACTICES",
    "GENERIC_PRACTICES",
    "SEED_PRACTICES",
    "Practice",
    "format_handbook_text",
    "generate_handbook",
    "get_practices",
    "get_seed_practices",
]
