"""specflow trace — Display the full traceability chain for an artifact."""

from __future__ import annotations

from pathlib import Path

from specflow.lib import artifacts as art_lib
from specflow.lib.display import RED, GREEN, CYAN, BOLD, DIM, NC


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


def _status_str(status: str) -> str:
    color = GREEN if status == "verified" else ""
    return f"{color}{status}{NC}" if color else status


def _find_children(parent_id: str, id_index: dict[str, art_lib.Artifact], role: str) -> list[art_lib.Artifact]:
    children = []
    for aid, art in id_index.items():
        if aid == parent_id:
            continue
        for link in art.links:
            if link.target == parent_id and link.role == role:
                children.append(art)
                break
    return children


def _find_parent(child_id: str, id_index: dict[str, art_lib.Artifact], role: str) -> art_lib.Artifact | None:
    child = id_index.get(child_id)
    if not child:
        return None
    for link in child.links:
        if link.role == role:
            parent = id_index.get(link.target)
            if parent:
                return parent
    return None


def _render_comp(artifact: art_lib.Artifact, id_index: dict[str, art_lib.Artifact]) -> int:
    print(f"\n{BOLD}{artifact.id}{NC}  {DIM}[{_format_type(artifact.type)}]{NC}  {artifact.title}  {_status_str(artifact.status)}")
    print()

    loops = _find_children(artifact.id, id_index, "operates_on")
    print(f"  {BOLD}Experimentation Loops ({len(loops)}):{NC}")
    if not loops:
        print(f"    {DIM}(none){NC}")
    for loop in loops:
        fm = loop.frontmatter
        mode = fm.get("mode", "")
        iterations = fm.get("iteration_count", fm.get("iterations", "?"))
        best_metric = fm.get("best_metric", "—")
        print(f"    {CYAN}{loop.id}{NC}  mode={mode}  iterations={iterations}  best_metric={best_metric}  {_status_str(loop.status)}")
        expts = _find_children(loop.id, id_index, "belongs_to")
        if expts:
            print(f"      {DIM}Experiments ({len(expts)}):{NC}")
            for expt in expts:
                expt_summary = expt.frontmatter.get("summary", expt.frontmatter.get("result", ""))
                print(f"        {CYAN}{expt.id}{NC}  {expt.title}  {_status_str(expt.status)}  {DIM}{expt_summary}{NC}")

    findings = [a for a in id_index.values()
                if a.id != artifact.id and art_lib.get_prefix_from_id(a.id) == "FIND"]
    comp_findings = []
    for f in findings:
        for link in f.links:
            if link.target == artifact.id and link.role == "belongs_to":
                comp_findings.append(f)
                break
    print()
    print(f"  {BOLD}Findings ({len(comp_findings)}):{NC}")
    if not comp_findings:
        print(f"    {DIM}(none){NC}")
    for finding in comp_findings:
        print(f"    {CYAN}{finding.id}{NC}  {finding.title}  {_status_str(finding.status)}")

    print()
    return 0


def _render_loop(artifact: art_lib.Artifact, id_index: dict[str, art_lib.Artifact]) -> int:
    print(f"\n{BOLD}{artifact.id}{NC}  {DIM}[{_format_type(artifact.type)}]{NC}  {artifact.title}  {_status_str(artifact.status)}")
    print()

    parent = _find_parent(artifact.id, id_index, "operates_on")
    print(f"  {BOLD}Parent Competition:{NC}")
    if parent:
        print(f"    {CYAN}{parent.id}{NC}  {parent.title}  {_status_str(parent.status)}")
    else:
        print(f"    {DIM}(none){NC}")

    expts = _find_children(artifact.id, id_index, "belongs_to")
    print()
    print(f"  {BOLD}Experiments ({len(expts)}):{NC}")
    if not expts:
        print(f"    {DIM}(none){NC}")
    for expt in expts:
        print(f"    {CYAN}{expt.id}{NC}  {expt.title}  {_status_str(expt.status)}")

    findings = [a for a in id_index.values()
                if art_lib.get_prefix_from_id(a.id) == "FIND"]
    loop_findings = []
    for f in findings:
        for link in f.links:
            if link.target == artifact.id and link.role == "condenses":
                loop_findings.append(f)
                break
    print()
    print(f"  {BOLD}Findings ({len(loop_findings)}):{NC}")
    if not loop_findings:
        print(f"    {DIM}(none){NC}")
    for finding in loop_findings:
        print(f"    {CYAN}{finding.id}{NC}  {finding.title}  {_status_str(finding.status)}")

    print()
    return 0


def _render_expt(artifact: art_lib.Artifact, id_index: dict[str, art_lib.Artifact]) -> int:
    print(f"\n{BOLD}{artifact.id}{NC}  {DIM}[{_format_type(artifact.type)}]{NC}  {artifact.title}  {_status_str(artifact.status)}")
    print()

    parent_loop = _find_parent(artifact.id, id_index, "belongs_to")
    print(f"  {BOLD}Parent Loop:{NC}")
    if parent_loop:
        print(f"    {CYAN}{parent_loop.id}{NC}  {parent_loop.title}  {_status_str(parent_loop.status)}")
    else:
        print(f"    {DIM}(none){NC}")

    parent_comp = _find_parent(parent_loop.id, id_index, "operates_on") if parent_loop else None
    print()
    print(f"  {BOLD}Competition:{NC}")
    if parent_comp:
        print(f"    {CYAN}{parent_comp.id}{NC}  {parent_comp.title}  {_status_str(parent_comp.status)}")
    else:
        print(f"    {DIM}(none){NC}")

    print()
    return 0


def run(root: Path, args: dict) -> int:
    artifact_id = args.get("artifact_id", "")
    if not artifact_id:
        print(f"{RED}✗ Missing required argument: <artifact-id>. "
              f"Usage: specflow trace <artifact-id>{NC}")
        return 1

    artifacts = art_lib.discover_artifacts(root)
    id_index = art_lib.build_id_index(artifacts)

    artifact = id_index.get(artifact_id)
    if not artifact:
        print(f"{RED}✗ Artifact '{artifact_id}' not found. "
              f"Run 'specflow status' to see all artifacts.{NC}")
        return 1

    prefix = art_lib.get_prefix_from_id(artifact_id)
    if prefix == "COMP":
        return _render_comp(artifact, id_index)
    if prefix == "LOOP":
        return _render_loop(artifact, id_index)
    if prefix == "EXPT":
        return _render_expt(artifact, id_index)

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
