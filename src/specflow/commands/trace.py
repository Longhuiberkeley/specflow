"""specflow trace — Display the full traceability chain for an artifact."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import GREEN, CYAN, NC

BOLD = "\033[1m"
DIM = "\033[2m"


def _format_type(art_type: str) -> str:
    return art_type.replace("-", " ").title()


def _print_tree(nodes: list[dict[str, str]], label: str, indent: str = "  ") -> None:
    if not nodes:
        print(f"{indent}{DIM}(none){NC}")
        return
    for node in nodes:
        type_label = _format_type(node.get("type", "unknown"))
        status = node.get("status", "")
        role = node.get("role", "")
        status_color = GREEN if status == "verified" else ""
        status_str = f"{status_color}{status}{NC}" if status_color else status
        print(f"{indent}{CYAN}{node['id']}{NC}  {DIM}[{type_label}]{NC}  {node.get('title', '')}  {status_str}  {DIM}({role}){NC}")


def run(root: Path, args: dict) -> int:
    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print("Usage: specflow trace <artifact-id>")
        return 1

    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)

    artifact = id_index.get(artifact_id)
    if not artifact:
        print(f"Artifact '{artifact_id}' not found")
        return 1

    chain = art_lib.trace_chain(artifact_id, id_index, direction="both")

    type_label = _format_type(artifact.type)
    status = artifact.status
    status_color = GREEN if status == "verified" else ""
    status_str = f"{status_color}{status}{NC}" if status_color else status

    print(f"\n{BOLD}{artifact_id}{NC}  {DIM}[{type_label}]{NC}  {artifact.title}  {status_str}")
    print()

    print(f"  {BOLD}Upstream (sources/standards):{NC}")
    _print_tree(chain["upstream"], "upstream", indent="    ")

    print()
    print(f"  {BOLD}Downstream (implementation/verification):{NC}")
    _print_tree(chain["downstream"], "downstream", indent="    ")

    print()
    depth_path = art_lib.compute_chain_depth(artifact_id, id_index)
    print(f"  {BOLD}Chain depth:{NC} {len(depth_path)} links  {DIM}({' -> '.join(depth_path)}){NC}")

    return 0
