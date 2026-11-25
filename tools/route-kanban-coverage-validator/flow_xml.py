"""Hardened reader and normalized exporter for CMF/Navigo flow XML."""
from __future__ import annotations
from hashlib import sha256
import re
from xml.etree import ElementTree as ET
from pydantic import BaseModel, ConfigDict, Field, model_validator

MAX_FLOW_XML_BYTES = 1_000_000

class FlowXmlValidationError(ValueError): pass

class FlowXmlStep(BaseModel):
    position: int = Field(gt=0)
    step_name: str
    step_ref_id: str
    flow_step_object_id: str
    correlation_id: str
    is_optional: bool
    is_skippable: bool
    is_source: bool
    is_line: bool
    model_config = ConfigDict(frozen=True)

class FlowXmlReworkPath(BaseModel):
    order: int = Field(gt=0)
    source_flow_path: str
    source_step_name: str
    goto_flow_path: str
    goto_step_name: str
    return_flow_path: str | None
    return_step_name: str | None
    model_config = ConfigDict(frozen=True)

class FlowXmlDocument(BaseModel):
    source_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cmf_format_version: str = Field(pattern=r"^1\.0$")
    navigo_business_object_version: str
    flow_name: str
    flow_version: str
    flow_id: str
    steps: tuple[FlowXmlStep, ...] = Field(min_length=1, max_length=1000)
    rework_paths: tuple[FlowXmlReworkPath, ...] = Field(max_length=1000)
    internal_identity_metadata_present: bool
    model_config = ConfigDict(frozen=True)

    @model_validator(mode="after")
    def validate_ordering(self):
        positions = [x.position for x in self.steps]
        if positions != list(range(1, len(positions) + 1)):
            raise ValueError("flow-step positions must be unique and contiguous from 1")
        orders = [x.order for x in self.rework_paths]
        if len(orders) != len(set(orders)):
            raise ValueError("duplicate rework-path order")
        return self

def _value(parent, path, label):
    node = parent.find(path)
    value = None if node is None or node.get("isNull") == "True" else node.get("value")
    if value is None or not value.strip(): raise FlowXmlValidationError(f"missing required {label}")
    return value.strip()

def _ref(parent, path, attribute, label):
    node = parent.find(path); value = None if node is None else node.get(attribute)
    if value is None or not value.strip(): raise FlowXmlValidationError(f"missing required {label}")
    return value.strip()

def _optional_value(parent, path):
    node = parent.find(path)
    if node is None or node.get("isNull") == "True": return None
    value = node.get("value")
    return value.strip() if value and value.strip() else None

def _optional_ref(parent, path, attribute):
    node = parent.find(path)
    if node is None or node.get("isNull") == "True": return None
    value = node.get(attribute)
    return value.strip() if value and value.strip() else None

def _integer(parent, path, label):
    try: result = int(_value(parent, path, label))
    except ValueError as exc: raise FlowXmlValidationError(f"invalid integer {label}") from exc
    if result <= 0: raise FlowXmlValidationError(f"nonpositive {label}")
    return result

def _boolean(parent, path, label):
    value = _value(parent, path, label).lower()
    if value not in {"true", "false"}: raise FlowXmlValidationError(f"invalid Boolean {label}")
    return value == "true"

def parse_flow_xml(content: bytes) -> FlowXmlDocument:
    if not content: raise FlowXmlValidationError("flow XML is empty")
    if len(content) > MAX_FLOW_XML_BYTES: raise FlowXmlValidationError("flow XML exceeds the one-megabyte limit")
    markup = content.upper()
    if b"<!DOCTYPE" in markup or b"<!ENTITY" in markup: raise FlowXmlValidationError("DTD and entity declarations are not allowed")
    try: root = ET.fromstring(content)
    except ET.ParseError as exc: raise FlowXmlValidationError("flow XML is not well formed") from exc
    if root.tag != "CMF.ExportFile" or root.get("version") != "1.0": raise FlowXmlValidationError("unsupported CMF export root or version")
    objects = root.findall("./Object")
    if len(objects) != 1 or "Cmf.Navigo.BusinessObjects.Flow," not in objects[0].get("type", ""): raise FlowXmlValidationError("exactly one Navigo flow object is required")
    flow = objects[0]
    version = re.search(r"\bVersion=([0-9.]+)", flow.get("type", ""))
    if version is None: raise FlowXmlValidationError("missing Navigo business-object version")
    steps = []
    flow_step_objects = [item for item in flow.iter("Object") if "Cmf.Navigo.BusinessObjects.FlowStep," in item.get("type", "")]
    for item in flow_step_objects:
        steps.append(FlowXmlStep(position=_integer(item,"./Position","flow-step position"), step_name=_ref(item,"./TargetEntity/ObjectRef","RefName","step name"), step_ref_id=_ref(item,"./TargetEntity/ObjectRef","RefId","step reference ID"), flow_step_object_id=_value(item,"./Id","flow-step object ID"), correlation_id=_value(item,"./CorrelationID","correlation ID"), is_optional=_boolean(item,"./IsOptional","IsOptional"), is_skippable=_boolean(item,"./IsSkippable","IsSkippable"), is_source=_boolean(item,"./IsSource","IsSource"), is_line=_boolean(item,"./IsLine","IsLine")))
    steps.sort(key=lambda x: x.position)
    rework = []
    for item in flow.findall("./ReworkPaths/Item/Object"):
        rework.append(FlowXmlReworkPath(order=_integer(item,"./Order","rework order"), source_flow_path=_value(item,"./SourceFlowPath","source path"), source_step_name=_ref(item,"./SourceStep/ObjectRef","RefName","source step"), goto_flow_path=_value(item,"./GotoFlowPath","goto path"), goto_step_name=_ref(item,"./GotoStep/ObjectRef","RefName","goto step"), return_flow_path=_optional_value(item,"./ReturnFlowPath"), return_step_name=_optional_ref(item,"./ReturnStep/ObjectRef","RefName")))
    rework.sort(key=lambda x: x.order)
    try:
        return FlowXmlDocument(source_sha256=sha256(content).hexdigest(), cmf_format_version=root.get("version"), navigo_business_object_version=version.group(1), flow_name=_value(flow,"./Name","flow name"), flow_version=_value(flow,"./Version","flow version"), flow_id=_value(flow,"./Id","flow ID"), steps=tuple(steps), rework_paths=tuple(rework), internal_identity_metadata_present=any(n.get("value") for n in root.findall(".//CreatedBy") + root.findall(".//ModifiedBy")))
    except ValueError as exc: raise FlowXmlValidationError("flow XML violates the normalized contract") from exc

def export_normalized_flow_xml(document: FlowXmlDocument) -> bytes:
    root = ET.Element("NGBFlowExchange", {"schemaVersion":"1.0","sourceSha256":document.source_sha256,"sourceFormat":"CMF.ExportFile","mesImportCompatible":"False"})
    flow = ET.SubElement(root,"Flow",{"name":document.flow_name,"version":document.flow_version,"sourceId":document.flow_id,"navigoBusinessObjectVersion":document.navigo_business_object_version})
    steps = ET.SubElement(flow,"Steps",{"count":str(len(document.steps))})
    for x in document.steps: ET.SubElement(steps,"Step",{"position":str(x.position),"name":x.step_name,"sourceRefId":x.step_ref_id,"sourceFlowStepId":x.flow_step_object_id,"sourceCorrelationId":x.correlation_id,"optional":str(x.is_optional),"skippable":str(x.is_skippable),"source":str(x.is_source),"line":str(x.is_line)})
    paths = ET.SubElement(flow,"ReworkPaths",{"count":str(len(document.rework_paths)),"promotionStatus":"REFERENCE_ONLY"})
    for x in document.rework_paths:
        attributes={"order":str(x.order),"sourceFlowPath":x.source_flow_path,"sourceStep":x.source_step_name,"gotoFlowPath":x.goto_flow_path,"gotoStep":x.goto_step_name}
        if x.return_flow_path is not None: attributes["returnFlowPath"]=x.return_flow_path
        if x.return_step_name is not None: attributes["returnStep"]=x.return_step_name
        ET.SubElement(paths,"ReworkPath",attributes)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)
