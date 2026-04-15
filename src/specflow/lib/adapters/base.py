"""Base adapter interface for SpecFlow's unified adapter framework.

All concrete adapters inherit from `Adapter` and implement only the operations
they support, declaring their surface via `supported_operations`.

Three axes:
  - CI generation: `generate_ci_workflow()`
  - Artifact exchange: `import_artifacts()`, `export_artifacts()`
  - Standards ingestion: `ingest_standard()`

See retrospective §11 and docs/authoring-an-adapter.md for the full spec.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class Adapter(ABC):
    """Unified adapter interface.

    Concrete adapters implement only the methods they need.
    `supported_operations` declares which methods are available.

    Subclasses must set:
        name: str                  # e.g. "github-actions", "reqif"
        supported_operations: set  # e.g. {"generate_ci_workflow"}
    """

    name: str = ""
    supported_operations: set[str] = set()

    # --- CI generation ---

    def generate_ci_workflow(self, ops: list[str]) -> dict[Path, str]:
        """Generate CI workflow files for the requested operations.

        Args:
            ops: List of operation names to generate workflows for
                 (e.g. "artifact-lint", "change-impact", "project-audit", "release-gate").

        Returns:
            dict mapping output Path to rendered string content.
        """
        raise NotImplementedError(
            f"{self.name} does not support 'generate_ci_workflow'"
        )

    # --- Artifact exchange ---

    def import_artifacts(self, source: Path) -> dict[str, Any]:
        """Import artifacts from an external exchange format.

        Args:
            source: Path to the source file.

        Returns:
            dict with at least {"ok": bool, "created": [ids], "skipped": [...]}.
        """
        raise NotImplementedError(
            f"{self.name} does not support 'import_artifacts'"
        )

    def export_artifacts(self, dest: Path) -> dict[str, Any]:
        """Export artifacts to an external exchange format.

        Args:
            dest: Path to write the exported file.

        Returns:
            dict with at least {"ok": bool, "written": int, "path": str}.
        """
        raise NotImplementedError(
            f"{self.name} does not support 'export_artifacts'"
        )

    # --- Standards ingestion ---

    def ingest_standard(self, source: Path) -> dict[str, Any]:
        """Ingest a standard document and produce a standards pack.

        Args:
            source: Path to the source document (PDF, YAML, etc.).

        Returns:
            dict describing the generated pack.
        """
        raise NotImplementedError(
            f"{self.name} does not support 'ingest_standard'"
        )

    # --- Hook script generation ---

    def get_hook_script(self) -> str:
        """Return the shell hook script for this CI provider.

        Returns:
            String content of the hook script (Bash, PowerShell, etc.).
        """
        raise NotImplementedError(
            f"{self.name} does not support 'get_hook_script'"
        )


# --- Registry ---

ADAPTER_REGISTRY: dict[str, type[Adapter]] = {}


def register_adapter(cls: type[Adapter]) -> type[Adapter]:
    """Class decorator: register an adapter in the global registry.

    Usage:
        @register_adapter
        class GitHubActionsAdapter(Adapter):
            name = "github-actions"
            supported_operations = {"generate_ci_workflow", "get_hook_script"}
    """
    if not cls.name:
        raise TypeError(
            f"Adapter class {cls.__name__} must define a non-empty `name`"
        )
    ADAPTER_REGISTRY[cls.name] = cls
    return cls


def get_adapter(name: str) -> Adapter:
    """Instantiate an adapter by name from the registry.

    Raises ValueError if no adapter is registered for *name*.
    """
    cls = ADAPTER_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(sorted(ADAPTER_REGISTRY)) or "none"
        raise ValueError(
            f"No adapter registered for '{name}'. Available: {available}"
        )
    return cls()
