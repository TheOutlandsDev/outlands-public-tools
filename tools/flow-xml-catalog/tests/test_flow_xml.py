import json
from pathlib import Path
from xml.etree import ElementTree as ET
import pytest
from production_planning.flow_xml import MAX_FLOW_XML_BYTES, FlowXmlValidationError, export_normalized_flow_xml, parse_flow_xml

ROOT=Path(__file__).resolve().parents[1]; INPUTS=ROOT/"data"/"flow_xml_inputs"
MANIFEST=json.loads((ROOT/"data"/"flow_xml_manifest.json").read_text())

@pytest.mark.parametrize("expected",MANIFEST["sources"])
def test_sources_match_manifest(expected):
    doc=parse_flow_xml((INPUTS/expected["filename"]).read_bytes())
    assert (doc.source_sha256,doc.flow_name,doc.flow_version)==(expected["sha256"],expected["flow_name"],expected["flow_version"])
    assert (len(doc.steps),len(doc.rework_paths))==(expected["step_count"],expected["rework_path_count"])
    assert doc.internal_identity_metadata_present is True

def test_control_flex_repeated_occurrences_are_preserved():
    doc=parse_flow_xml((INPUTS/"demo-circuit-6.xml").read_bytes()); rows=[x for x in doc.steps if x.step_name=="Repeated_Check"]
    assert [x.position for x in rows]==[15,26,28]
    assert {x.step_ref_id for x in rows}=={"DEMO-REF-REPEAT"}
    assert [x.correlation_id for x in rows]==["15","20","22"]

def test_export_is_bounded_and_not_claimed_mes_compatible():
    exported=export_normalized_flow_xml(parse_flow_xml((INPUTS/"demo-panel-7.xml").read_bytes())); root=ET.fromstring(exported)
    assert root.tag=="NGBFlowExchange" and root.get("mesImportCompatible")=="False"
    assert len(root.findall("./Flow/Steps/Step"))==38
    assert root.find("./Flow/ReworkPaths").get("promotionStatus")=="REFERENCE_ONLY"
    assert b"CreatedBy" not in exported and b"ModifiedBy" not in exported and b"DEMO\\" not in exported

@pytest.mark.parametrize("content,message",[(b"","empty"),(b"<!DOCTYPE x><CMF.ExportFile/>","DTD"),(b"<!ENTITY x 'y'><CMF.ExportFile/>","entity"),(b"<wrong/>","unsupported"),(b"<CMF.ExportFile>","well formed"),(b"x"*(MAX_FLOW_XML_BYTES+1),"one-megabyte")])
def test_unsafe_xml_fails_closed(content,message):
    with pytest.raises(FlowXmlValidationError,match=message): parse_flow_xml(content)

def test_dtd_after_first_four_kilobytes_fails_closed():
    content = (b" " * 5000) + b"<!DOCTYPE x><CMF.ExportFile/>"
    with pytest.raises(FlowXmlValidationError, match="DTD"):
        parse_flow_xml(content)

def test_duplicate_position_fails_closed():
    root=ET.fromstring((INPUTS/"demo-circuit-6.xml").read_bytes()); flow=root.find("./Object"); objects=[x for x in flow.iter("Object") if "Cmf.Navigo.BusinessObjects.FlowStep," in x.get("type","")]; positions=[x.find("./Position") for x in objects]; positions[1].set("value",positions[0].get("value"))
    with pytest.raises(FlowXmlValidationError,match="normalized contract"): parse_flow_xml(ET.tostring(root,encoding="utf-8"))
