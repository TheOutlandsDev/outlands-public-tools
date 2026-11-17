from pathlib import Path
import importlib.util
import py_compile
import tempfile
import textwrap

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "panel_overlay_aggregate_v2_axisfix.py"

py_compile.compile(str(SCRIPT), doraise=True)

spec = importlib.util.spec_from_file_location("agg_axisfix", str(SCRIPT))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

xml_text = textwrap.dedent("""
<Body>
  <Site ID="1">
    <Measurements>
      <Measurement ID="LL_L2_VX" type="OL" status="OK"><Result>-0.250000</Result><MeasurementMarkData><MeasurementType>OVL_LN_LN</MeasurementType></MeasurementMarkData></Measurement>
      <Measurement ID="LL_L2_VY" type="OL" status="OK"><Result>0.750000</Result><MeasurementMarkData><MeasurementType>OVL_LN_LN</MeasurementType></MeasurementMarkData></Measurement>
      <Measurement ID="UR_L2_VX" type="OL" status="OK"><Result>-0.500000</Result><MeasurementMarkData><MeasurementType>OVL_LN_LN</MeasurementType></MeasurementMarkData></Measurement>
      <Measurement ID="UR_L2_VY" type="OL" status="OK"><Result>0.125000</Result><MeasurementMarkData><MeasurementType>OVL_LN_LN</MeasurementType></MeasurementMarkData></Measurement>
      <Measurement ID="LL_L2_V" type="CD" status="OK"><Result>8.000000</Result><MeasurementMarkData><MeasurementType>CD</MeasurementType></MeasurementMarkData></Measurement>
    </Measurements>
  </Site>
</Body>
""").strip()

with tempfile.TemporaryDirectory() as td:
    xml_path = Path(td) / "sample.xml"
    xml_path.write_text(xml_text, encoding="utf-8")
    parsed = mod.read_cdo_overlay_measurements(xml_path)

assert parsed["LL_L2_VX"] == -0.250000
assert parsed["LL_L2_VY"] == 0.750000
assert parsed["UR_L2_VX"] == -0.500000
assert parsed["UR_L2_VY"] == 0.125000
assert "LL_L2" not in parsed

panel_map_new = {
    "SYNTHETIC-PANEL-01": {
        "LL_L2_VX": [(-0.500000, 0.100000)],
        "LL_L2_VY": [(0.600000, 0.200000)],
    }
}
panel_map_old = {
    "SYNTHETIC-PANEL-01": {
        "LL_L2_VX": -0.250000,
        "LL_L2_VY": 0.750000,
    }
}
rows = mod.panel_rows(panel_map_new, panel_map_old)
row = rows[0]
assert row["CDO_LL_L2_VX"] == "-0.250000"
assert row["CDO_LL_L2_VY"] == "0.750000"
assert row["DIFF_LL_L2_VX"] == f"{-0.500000 - (-0.250000):.6f}"
assert row["DIFF_LL_L2_VY"] == f"{0.600000 - 0.750000:.6f}"

print("syntax_ok=True")
print("overlay_axis_keys_ok=True")
print("axis_specific_row_mapping_ok=True")
