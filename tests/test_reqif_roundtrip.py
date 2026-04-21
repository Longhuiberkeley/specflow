"""Tests for ReqIF round-trip quality: deterministic UUIDs, ARCH/DDD export, import."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
import pytest

from specflow.lib import reqif as reqif_lib
from specflow.lib import artifacts as art_lib


REQIF_NS = "http://www.omg.org/spec/ReqIF/20110401/reqif.xsd"


@pytest.fixture
def project_root(tmp_path: Path):
    specflow = tmp_path / "_specflow"
    for subdir in ["specs/requirements", "specs/architecture", "specs/detailed-design"]:
        (specflow / subdir).mkdir(parents=True, exist_ok=True)

    schema_dir = tmp_path / ".specflow" / "schema"
    schema_dir.mkdir(parents=True, exist_ok=True)

    for art_type, prefix in [("requirement", "REQ"), ("architecture", "ARCH"), ("detailed-design", "DDD")]:
        schema = {
            "type": art_type,
            "prefix": prefix,
            "allowed_status": {"draft": [], "approved": ["draft"], "implemented": ["approved"], "verified": ["implemented"]},
        }
        (schema_dir / f"{art_type}.yaml").write_text(yaml.dump(schema), encoding="utf-8")

    return tmp_path


def _write_artifact(root: Path, art_type: str, art_id: str, title: str, status: str,
                    body: str = "", **extra_fm) -> Path:
    rel_dir = art_lib.TYPE_TO_DIR.get(art_type, f"specs/{art_type}")
    target_dir = root / "_specflow" / rel_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    fm = {"id": art_id, "title": title, "type": art_type, "status": status, "suspect": False,
          "links": [], "created": "2026-04-21"}
    fm.update(extra_fm)
    content = f"---\n{yaml.dump(fm, default_flow_style=False, sort_keys=False)}---\n\n{body}\n"
    path = target_dir / f"{art_id}.md"
    path.write_text(content, encoding="utf-8")
    return path


class TestDeterministicUUIDs:
    def test_export_twice_same_uuids(self, project_root):
        _write_artifact(project_root, "requirement", "REQ-001", "Test Req", "approved", body="Body text.")

        out1 = project_root / "export1.reqif"
        out2 = project_root / "export2.reqif"

        r1 = reqif_lib.export_reqif(project_root, out1)
        r2 = reqif_lib.export_reqif(project_root, out2)

        assert r1["ok"] and r2["ok"]

        xml1 = out1.read_text(encoding="utf-8")
        xml2 = out2.read_text(encoding="utf-8")

        tree1 = ET.fromstring(xml1)
        tree2 = ET.fromstring(xml2)

        ns = {"r": REQIF_NS}
        ids1 = [el.attrib.get("IDENTIFIER", "") for el in tree1.findall(".//r:SPEC-OBJECT", ns)]
        ids2 = [el.attrib.get("IDENTIFIER", "") for el in tree2.findall(".//r:SPEC-OBJECT", ns)]
        assert ids1 == ids2

        hdr1 = tree1.find(".//r:REQ-IF-HEADER", ns)
        hdr2 = tree2.find(".//r:REQ-IF-HEADER", ns)
        assert hdr1 is not None and hdr2 is not None
        assert hdr1.attrib.get("IDENTIFIER") == hdr2.attrib.get("IDENTIFIER")

    def test_internal_id_stability(self, project_root):
        _write_artifact(project_root, "requirement", "REQ-001", "A", "approved")

        out = project_root / "out.reqif"
        reqif_lib.export_reqif(project_root, out)

        id1 = reqif_lib._new_id("test", "seed-123")
        id2 = reqif_lib._new_id("test", "seed-123")
        assert id1 == id2

    def test_different_seeds_different_ids(self):
        id1 = reqif_lib._new_id("test", "seed-a")
        id2 = reqif_lib._new_id("test", "seed-b")
        assert id1 != id2


class TestExportArchAndDdd:
    def test_arch_appears_in_export(self, project_root):
        _write_artifact(project_root, "requirement", "REQ-001", "Req", "approved", body="Req body.")
        _write_artifact(project_root, "architecture", "ARCH-001", "Arch", "approved", body="Arch body.")

        out = project_root / "out.reqif"
        result = reqif_lib.export_reqif(project_root, out)
        assert result["ok"]
        assert result["written"] == 2

        tree = ET.fromstring(out.read_text(encoding="utf-8"))
        ns = {"r": REQIF_NS}
        objects = tree.findall(".//r:SPEC-OBJECT", ns)
        obj_ids = [el.attrib.get("IDENTIFIER", "") for el in objects]
        assert "REQ-001" in obj_ids
        assert "ARCH-001" in obj_ids

    def test_ddd_appears_in_export(self, project_root):
        _write_artifact(project_root, "detailed-design", "DDD-001", "Design", "approved", body="Design body.")

        out = project_root / "out.reqif"
        result = reqif_lib.export_reqif(project_root, out)
        assert result["ok"]
        assert result["written"] == 1

        tree = ET.fromstring(out.read_text(encoding="utf-8"))
        ns = {"r": REQIF_NS}
        objects = tree.findall(".//r:SPEC-OBJECT", ns)
        obj_ids = [el.attrib.get("IDENTIFIER", "") for el in objects]
        assert "DDD-001" in obj_ids

    def test_specflow_type_attribute_in_export(self, project_root):
        _write_artifact(project_root, "architecture", "ARCH-001", "Arch", "approved", body="Arch body.")

        out = project_root / "out.reqif"
        reqif_lib.export_reqif(project_root, out)

        tree = ET.fromstring(out.read_text(encoding="utf-8"))
        ns = {"r": REQIF_NS}
        values = tree.findall(".//r:SPEC-OBJECT/r:VALUES/r:ATTRIBUTE-VALUE-STRING", ns)
        type_found = False
        for v in values:
            defn = v.find("r:DEFINITION", ns)
            if defn is not None:
                for child in defn:
                    if child.attrib.get("LONG-NAME") == "SpecFlow.Type":
                        type_found = True
                        assert v.attrib.get("THE-VALUE") == "architecture"
        assert type_found


class TestImportRoundTrip:
    def test_import_creates_req_artifacts(self, project_root):
        reqif_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF xmlns="{REQIF_NS}">
  <CORE-CONTENT>
    <REQ-IF-CONTENT>
      <SPEC-OBJECTS>
        <SPEC-OBJECT IDENTIFIER="ext-001" LONG-NAME="Imported Requirement">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="Imported Requirement">
              <DEFINITION><ATTRIBUTE-DEFINITION-STRING IDENTIFIER="ad1" LONG-NAME="ReqIF.Name"/></DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="This is the body.">
              <DEFINITION><ATTRIBUTE-DEFINITION-STRING IDENTIFIER="ad2" LONG-NAME="ReqIF.Text"/></DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
          </VALUES>
        </SPEC-OBJECT>
      </SPEC-OBJECTS>
    </REQ-IF-CONTENT>
  </CORE-CONTENT>
</REQ-IF>"""
        reqif_file = project_root / "import.reqif"
        reqif_file.write_text(reqif_xml, encoding="utf-8")

        result = reqif_lib.import_reqif(project_root, reqif_file)
        assert result["ok"]
        assert len(result["created"]) == 1
        assert len(result["skipped"]) == 0

        created_id = result["created"][0]
        artifacts = art_lib.discover_artifacts(project_root, "requirement")
        assert any(a.id == created_id for a in artifacts)

    def test_import_preserves_extra_attrs(self, project_root):
        reqif_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<REQ-IF xmlns="{REQIF_NS}">
  <CORE-CONTENT>
    <REQ-IF-CONTENT>
      <SPEC-OBJECTS>
        <SPEC-OBJECT IDENTIFIER="ext-002" LONG-NAME="With Extras">
          <VALUES>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="With Extras">
              <DEFINITION><ATTRIBUTE-DEFINITION-STRING IDENTIFIER="ad1" LONG-NAME="ReqIF.Name"/></DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="Body text">
              <DEFINITION><ATTRIBUTE-DEFINITION-STRING IDENTIFIER="ad2" LONG-NAME="ReqIF.Text"/></DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
            <ATTRIBUTE-VALUE-STRING THE-VALUE="custom-value-123">
              <DEFINITION><ATTRIBUTE-DEFINITION-STRING IDENTIFIER="ad3" LONG-NAME="IBM_DOORS_CustomAttr"/></DEFINITION>
            </ATTRIBUTE-VALUE-STRING>
          </VALUES>
        </SPEC-OBJECT>
      </SPEC-OBJECTS>
    </REQ-IF-CONTENT>
  </CORE-CONTENT>
</REQ-IF>"""
        reqif_file = project_root / "import.reqif"
        reqif_file.write_text(reqif_xml, encoding="utf-8")

        result = reqif_lib.import_reqif(project_root, reqif_file)
        assert result["ok"]
        created_id = result["created"][0]

        artifacts = art_lib.discover_artifacts(project_root, "requirement")
        art = next(a for a in artifacts if a.id == created_id)
        metadata = art.frontmatter.get("reqif_metadata", {})
        assert metadata.get("IBM_DOORS_CustomAttr") == "custom-value-123"
