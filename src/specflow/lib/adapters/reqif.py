"""ReqIF exchange adapter.

Ports the existing `lib/reqif.py` import/export logic behind the Adapter interface.
Zero behavioral regression — the underlying functions are called directly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from specflow.lib.adapters.base import Adapter, register_adapter
from specflow.lib import reqif as _reqif_lib


@register_adapter
class ReqIFAdapter(Adapter):
    """Bidirectional ReqIF exchange adapter."""

    name = "reqif"
    supported_operations = {"import_artifacts", "export_artifacts"}

    def import_artifacts(self, source: Path) -> dict[str, Any]:
        """Import requirements from a ReqIF XML file.

        Delegates to the existing lib/reqif.import_reqif() function.
        Returns {"ok": bool, "created": [ids], "skipped": [...]}.
        """
        root = Path.cwd()
        # The underlying lib expects a project root; use cwd.
        return _reqif_lib.import_reqif(root, source)

    def export_artifacts(self, dest: Path) -> dict[str, Any]:
        """Export requirements to a ReqIF XML file.

        Delegates to the existing lib/reqif.export_reqif() function.
        Returns {"ok": bool, "written": int, "path": str}.
        """
        root = Path.cwd()
        return _reqif_lib.export_reqif(root, dest)
