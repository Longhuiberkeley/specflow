"""ReqIF 1.2 core import/export.

Target: OMG ReqIF 1.2 core spec. We emit and parse the subset of elements
needed for requirement interchange with DOORS/Polarion:

  REQ-IF
    CORE-CONTENT
      REQ-IF-CONTENT
        DATATYPES/SPEC-TYPES   — minimal schema for our attributes
        SPEC-OBJECTS            — one per requirement
        SPECIFICATIONS          — one root specification grouping all SpecObjects

Tool-specific attributes (DOORS `IBM_DOORS_*`, Polarion `polarion:*`) are
preserved verbatim in the artifact's `reqif_metadata` frontmatter field so
round-trips do not lose information.
"""

from __future__ import annotations

import datetime as _dt
import html
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from specflow.lib import artifacts as art_lib


REQIF_NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"
XHTML_NS = "http://www.w3.org/1999/xhtml"

_CORE_ATTRS = {
    "ReqIF.Name": "title",
    "ReqIF.Text": "body",
    "ReqIF.Description": "rationale",
    "SpecFlow.Status": "status",
    "SpecFlow.Priority": "priority",
    "SpecFlow.Tags": "tags",
}


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


def import_reqif(root: Path, file_path: Path) -> dict[str, Any]:
    """Parse a ReqIF XML file and create REQ-*.md artifacts for every SpecObject.

    Returns {ok, created: [ids], skipped: [{id, reason}]}.
    """
    if not file_path.is_file():
        return {"ok": False, "error": f"file not found: {file_path}"}

    try:
        tree = ET.parse(str(file_path))
    except ET.ParseError as exc:
        return {"ok": False, "error": f"invalid ReqIF XML: {exc}"}

    ns = {"r": REQIF_NS}
    root_el = tree.getroot()
    spec_objects = root_el.findall(".//r:SPEC-OBJECT", ns)
    if not spec_objects:
        # Fall back: try without namespace (some exports are namespace-free).
        spec_objects = root_el.findall(".//SPEC-OBJECT")

    created: list[str] = []
    skipped: list[dict[str, str]] = []

    for spec_obj in spec_objects:
        fields = _extract_spec_object_fields(spec_obj, ns)
        title = fields.pop("title", "") or fields.get("identifier", "Imported requirement")
        body = fields.pop("body", "")
        status = fields.pop("status", "draft")
        priority = fields.pop("priority", None)
        rationale = fields.pop("rationale", None)
        tags_raw = fields.pop("tags", "")
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else None

        identifier = fields.pop("identifier", "")
        reqif_metadata = {k: v for k, v in fields.items() if v is not None}
        if identifier:
            reqif_metadata["identifier"] = identifier

        result = art_lib.create_artifact(
            root=root,
            artifact_type="requirement",
            title=title,
            status=status if status in ("draft", "approved", "implemented", "verified") else "draft",
            priority=priority,
            rationale=rationale,
            tags=tags,
            body=body,
        )

        if not result.get("ok"):
            skipped.append({"id": identifier, "reason": result.get("error", "unknown")})
            continue

        # Persist unmapped ReqIF attributes under reqif_metadata.
        if reqif_metadata:
            art_lib.update_artifact(
                root=root,
                artifact_id=result["id"],
                reqif_metadata=reqif_metadata,
            )
        created.append(result["id"])

    return {"ok": True, "created": created, "skipped": skipped}


def _extract_spec_object_fields(spec_obj: ET.Element, ns: dict[str, str]) -> dict[str, Any]:
    """Pull known SpecFlow/ReqIF attributes out of a SPEC-OBJECT element.

    Everything that doesn't match `_CORE_ATTRS` is returned as an "extra"
    attribute under its ReqIF name, for round-trip preservation.
    """
    out: dict[str, Any] = {}
    out["identifier"] = spec_obj.attrib.get("IDENTIFIER", "") or spec_obj.attrib.get("identifier", "")

    values_el = spec_obj.find("r:VALUES", ns) or spec_obj.find("VALUES")
    if values_el is None:
        return out

    for attr_val in list(values_el):
        tag = _localname(attr_val.tag)
        # The attribute definition reference tells us which attribute this is.
        def_el = _find_definition_ref(attr_val, ns)
        if def_el is None:
            continue
        long_name = def_el.attrib.get("LONG-NAME") or def_el.attrib.get("long-name") or ""
        # The THE-VALUE attribute or child holds the text.
        raw_value = _read_attr_value(attr_val, tag, ns)

        mapped = _CORE_ATTRS.get(long_name)
        if mapped:
            out[mapped] = raw_value
        elif long_name:
            out[long_name] = raw_value

    return out


def _localname(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _find_definition_ref(attr_val_el: ET.Element, ns: dict[str, str]) -> ET.Element | None:
    """The ReqIF `ATTRIBUTE-VALUE-*` elements carry a `DEFINITION` child.

    The definition itself references a data-type; we proxy it via attributes
    on the definition element (LONG-NAME) so importers don't need the full
    schema to map attributes by name.
    """
    defn = attr_val_el.find("r:DEFINITION", ns) or attr_val_el.find("DEFINITION")
    if defn is None:
        return None
    # DEFINITION contains an ATTRIBUTE-DEFINITION-* child with LONG-NAME.
    for child in list(defn):
        return child
    return None


def _read_attr_value(attr_val_el: ET.Element, tag: str, ns: dict[str, str]) -> Any:
    """Read the value from an ATTRIBUTE-VALUE-* element.

    Supported: STRING/ENUMERATION (attribute THE-VALUE), XHTML (child THE-VALUE
    with nested xhtml:div content).
    """
    if tag in ("ATTRIBUTE-VALUE-STRING", "ATTRIBUTE-VALUE-ENUMERATION",
               "ATTRIBUTE-VALUE-INTEGER", "ATTRIBUTE-VALUE-BOOLEAN"):
        return attr_val_el.attrib.get("THE-VALUE", "")
    if tag == "ATTRIBUTE-VALUE-XHTML":
        the_value = attr_val_el.find("r:THE-VALUE", ns) or attr_val_el.find("THE-VALUE")
        if the_value is None:
            return ""
        # Concatenate inner text, stripping XHTML tags.
        return "".join(the_value.itertext()).strip()
    return attr_val_el.attrib.get("THE-VALUE", "")


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


def export_reqif(root: Path, output_path: Path) -> dict[str, Any]:
    """Walk _specflow/specs/requirements/*.md and emit a ReqIF 1.2 XML file.

    Returns {ok, written: int, path}.
    """
    requirements = [
        a for a in art_lib.discover_artifacts(root, "requirement")
    ]
    if not requirements:
        return {"ok": False, "error": "no requirements found under _specflow/specs/requirements/"}

    req_if = ET.Element("REQ-IF", {"xmlns": REQIF_NS})
    header = ET.SubElement(req_if, "THE-HEADER")
    hdr = ET.SubElement(header, "REQ-IF-HEADER", {"IDENTIFIER": _new_id("hdr")})
    ET.SubElement(hdr, "CREATION-TIME").text = _dt.datetime.now(_dt.timezone.utc).isoformat()
    ET.SubElement(hdr, "REQ-IF-TOOL-ID").text = "SpecFlow"
    ET.SubElement(hdr, "REQ-IF-VERSION").text = "1.2"
    ET.SubElement(hdr, "SOURCE-TOOL-ID").text = "SpecFlow"
    ET.SubElement(hdr, "TITLE").text = "SpecFlow Requirements Export"

    core = ET.SubElement(req_if, "CORE-CONTENT")
    content = ET.SubElement(core, "REQ-IF-CONTENT")

    datatypes = ET.SubElement(content, "DATATYPES")
    dt_string_id = _new_id("dt-string")
    ET.SubElement(
        datatypes,
        "DATATYPE-DEFINITION-STRING",
        {"IDENTIFIER": dt_string_id, "LONG-NAME": "T_String", "MAX-LENGTH": "32000"},
    )

    spec_types = ET.SubElement(content, "SPEC-TYPES")
    spec_object_type_id = _new_id("sot")
    sot = ET.SubElement(
        spec_types,
        "SPEC-OBJECT-TYPE",
        {"IDENTIFIER": spec_object_type_id, "LONG-NAME": "SpecFlow Requirement"},
    )
    sot_attrs = ET.SubElement(sot, "SPEC-ATTRIBUTES")
    attr_def_ids: dict[str, str] = {}
    for long_name in _CORE_ATTRS.keys():
        attr_id = _new_id("adef")
        attr_def_ids[long_name] = attr_id
        attr_def = ET.SubElement(
            sot_attrs,
            "ATTRIBUTE-DEFINITION-STRING",
            {"IDENTIFIER": attr_id, "LONG-NAME": long_name},
        )
        dt_ref = ET.SubElement(attr_def, "TYPE")
        ET.SubElement(dt_ref, "DATATYPE-DEFINITION-STRING-REF").text = dt_string_id

    specification_type_id = _new_id("spt")
    spt = ET.SubElement(
        spec_types,
        "SPECIFICATION-TYPE",
        {"IDENTIFIER": specification_type_id, "LONG-NAME": "SpecFlow Specification"},
    )

    spec_objects_el = ET.SubElement(content, "SPEC-OBJECTS")
    specs_el = ET.SubElement(content, "SPECIFICATIONS")
    specification = ET.SubElement(
        specs_el,
        "SPECIFICATION",
        {"IDENTIFIER": _new_id("spec"), "LONG-NAME": "SpecFlow Requirements"},
    )
    ET.SubElement(
        ET.SubElement(specification, "TYPE"),
        "SPECIFICATION-TYPE-REF",
    ).text = specification_type_id
    children_el = ET.SubElement(specification, "CHILDREN")

    written = 0
    for req in requirements:
        identifier = req.id
        so = ET.SubElement(
            spec_objects_el,
            "SPEC-OBJECT",
            {"IDENTIFIER": identifier, "LONG-NAME": req.title or identifier},
        )
        ET.SubElement(
            ET.SubElement(so, "TYPE"),
            "SPEC-OBJECT-TYPE-REF",
        ).text = spec_object_type_id
        values = ET.SubElement(so, "VALUES")

        mapping = {
            "ReqIF.Name": req.title,
            "ReqIF.Text": req.body,
            "ReqIF.Description": req.frontmatter.get("rationale", "") or "",
            "SpecFlow.Status": req.status,
            "SpecFlow.Priority": req.frontmatter.get("priority", "") or "",
            "SpecFlow.Tags": ",".join(req.tags),
        }
        for long_name, value in mapping.items():
            attr = ET.SubElement(
                values,
                "ATTRIBUTE-VALUE-STRING",
                {"THE-VALUE": html.escape(str(value or ""), quote=True)},
            )
            defn = ET.SubElement(attr, "DEFINITION")
            ET.SubElement(defn, "ATTRIBUTE-DEFINITION-STRING", {
                "IDENTIFIER": attr_def_ids[long_name],
                "LONG-NAME": long_name,
            })

        # Round-trip preserved attributes
        preserved = req.frontmatter.get("reqif_metadata") or {}
        if isinstance(preserved, dict):
            for k, v in preserved.items():
                if k in ("identifier",):
                    continue
                attr = ET.SubElement(
                    values,
                    "ATTRIBUTE-VALUE-STRING",
                    {"THE-VALUE": html.escape(str(v or ""), quote=True)},
                )
                defn = ET.SubElement(attr, "DEFINITION")
                ET.SubElement(defn, "ATTRIBUTE-DEFINITION-STRING", {
                    "IDENTIFIER": _new_id("adef-extra"),
                    "LONG-NAME": k,
                })

        hier = ET.SubElement(
            children_el,
            "SPEC-HIERARCHY",
            {"IDENTIFIER": _new_id("sh")},
        )
        obj_ref = ET.SubElement(hier, "OBJECT")
        ET.SubElement(obj_ref, "SPEC-OBJECT-REF").text = identifier
        written += 1

    tree = ET.ElementTree(req_if)
    ET.indent(tree, space="  ")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(output_path), xml_declaration=True, encoding="utf-8")
    return {"ok": True, "written": written, "path": str(output_path)}


def _new_id(prefix: str) -> str:
    return f"_{prefix}-{uuid.uuid4().hex[:10]}"
