from __future__ import annotations
import argparse
import csv
import sys
import re
import math
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from statistics import median
import xml.etree.ElementTree as ET

# ============================================================
# TOML config
# ============================================================
try:
    import tomllib
except Exception:
    tomllib = None


def load_cfg(path: Optional[str]) -> dict:
    if not path or tomllib is None:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("rb") as f:
        return tomllib.load(f) or {}


def _get(d: dict, *path, default=None):
    cur = d
    for k in path:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(k)
    return cur if cur is not None else default


# ============================================================
# Analyzer import
# ============================================================
def import_analyzer(analyzer_path: Path):
    import importlib.util

    spec = importlib.util.spec_from_file_location("vernier_anl", str(analyzer_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import analyzer from {analyzer_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["vernier_anl"] = mod
    spec.loader.exec_module(mod)
    return mod


# ============================================================
# Measurement definitions
# ============================================================
MEAS_ORDER = [
    "UL_L2_VX",
    "UR_L2_VX",
    "LR_L2_VX",
    "LL_L2_VX",
    "UL_L2_VY",
    "UR_L2_VY",
    "LR_L2_VY",
    "LL_L2_VY",
]
CSV_HEADER = (
    ["Panel ID"]
    + MEAS_ORDER
    + [f"SIG_{k}" for k in MEAS_ORDER]
    + [f"CDO_{k}" for k in MEAS_ORDER]
    + [f"DIFF_{k}" for k in MEAS_ORDER]
)
CORNER_RE = re.compile(r"^(UL|UR|LR|LL)_L(\d+)", re.IGNORECASE)
AOI_AXIS_RE = re.compile(r"^(UL|UR|LR|LL)_L2_(VX|VY)$", re.IGNORECASE)
AOI_LEGACY_RE = re.compile(r"^(UL|UR|LR|LL)_L2$", re.IGNORECASE)


# ============================================================
# Helpers
# ============================================================
def panel_id_from_glass(glass_id: str) -> str:
    g = (glass_id or "").strip()
    if len(g) >= 3 and g[1] == "-" and g[0] in ("T", "B"):
        return g[2:]
    return g


def parse_corner_layer_from_geom(geom: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    if not geom:
        return None, None
    token = geom.split("^", 1)[0]
    m = CORNER_RE.match(token)
    if not m:
        return None, None
    return m.group(1).upper(), f"L{m.group(2)}"


def axis_from_class(cls_name: str) -> Optional[str]:
    nm = (cls_name or "").lower()
    if nm.startswith("vernier_h"):
        return "VX"
    if nm.startswith("vernier_v"):
        return "VY"
    return None


def read_manifests(out_root: Path) -> List[Path]:
    manifests = []
    manifests.extend(out_root.rglob("sites_manifest.csv"))
    manifests.extend(out_root.rglob("sites_manifest_tiff.csv"))
    # stable / unique ordering
    return sorted({p.resolve() for p in manifests})


def row_get(row: dict, *names: str) -> str:
    for name in names:
        val = row.get(name)
        if val is None:
            continue
        sval = str(val).strip()
        if sval:
            return sval
    return ""


# ============================================================
# Vern_Analyze wrapper
# ============================================================
def compute_alignment(anl, crop_path: Path, axis: str, verbose: bool):
    try:
        rgb, gray = anl.load_image_as_arrays(str(crop_path))
        h, w = gray.shape
        if axis == "VX":
            orientation = "landscape"
            group_a = anl.validate_indices(anl.LANDSCAPE_ROWS_GROUP_A, h)
            group_b = anl.validate_indices(anl.LANDSCAPE_ROWS_GROUP_B, h)
        else:
            orientation = "portrait"
            group_a = anl.validate_indices(anl.PORTRAIT_COLS_GROUP_A, w)
            group_b = anl.validate_indices(anl.PORTRAIT_COLS_GROUP_B, w)
        res = anl.plot_profiles_and_compute_alignment(
            gray, rgb, orientation, group_a, group_b, show_plots=False
        )
        return res.get("delta_um"), res.get("delta_sem_um")
    except Exception as e:
        if verbose:
            print(f"[WARN] analysis failed for {crop_path}: {e}")
        return None, None


# ============================================================
# CDO XML parsing (manifest-driven)
# ============================================================
def is_overlay_measurement(meas: ET.Element) -> bool:
    m_type_attr = (meas.attrib.get("type") or "").strip().upper()
    mark_type = (meas.findtext("./MeasurementMarkData/MeasurementType") or "").strip().upper()
    return (
        m_type_attr in {"OL", "OVL", "OVERLAY"}
        or mark_type in {"OVL_LN_LN", "OVL", "OL", "OVERLAY"}
    )


def read_cdo_overlay_measurements(cdo_xml: Path) -> Dict[str, float]:
    """
    Read AOI overlay values as axis-specific keys, e.g. LL_L2_VX / LL_L2_VY.
    Falls back to legacy corner-only keys only if those are present in older XMLs.
    """
    out: Dict[str, float] = {}
    root = ET.parse(str(cdo_xml)).getroot()
    for meas in root.iter("Measurement"):
        mid = (meas.attrib.get("ID") or "").strip().upper()
        if not mid:
            continue
        base = mid.split("^", 1)[0]
        node = meas.find("Result")
        if node is None or not node.text:
            continue
        try:
            value = float(node.text.strip())
        except Exception:
            continue

        if is_overlay_measurement(meas):
            m_axis = AOI_AXIS_RE.match(base)
            if m_axis:
                corner, axis = m_axis.groups()
                out[f"{corner}_L2_{axis}"] = value
                continue
            m_legacy = AOI_LEGACY_RE.match(base)
            if m_legacy:
                # retained only as compatibility fallback
                out[f"{m_legacy.group(1)}_L2"] = value
    return out


# ============================================================
# Aggregation
# ============================================================
def aggregate_from_manifest(
    manifest: Path,
    anl,
    panel_map_new,
    panel_map_old,
    verbose: bool,
):
    cdo_cache: Dict[str, Dict[str, float]] = {}
    with open(manifest, "r", encoding="utf-8") as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            panel = panel_id_from_glass(
                row_get(row, "glass_id", "GlassID", "glass", "GlassId")
            )

            # -------- CDO / AOI reference --------
            cdo_path_str = row_get(row, "cdo_xml_path", "cdo_path", "cdo_xml", "cdo")
            if cdo_path_str and panel and panel not in cdo_cache:
                cdo_path = Path(cdo_path_str)
                if cdo_path.exists():
                    if verbose:
                        print(f"[INFO] Using AOI XML for panel {panel}: {cdo_path}")
                    cdo_cache[panel] = read_cdo_overlay_measurements(cdo_path)
            if panel in cdo_cache and panel not in panel_map_old:
                panel_map_old[panel] = cdo_cache[panel]

            # -------- YOLO / analyzer --------
            geom = row_get(row, "geom_name", "geom", "GeometryID", "geometry_id")
            corner, layer = parse_corner_layer_from_geom(geom)
            axis = axis_from_class(row_get(row, "class_yolo", "class_name", "class"))
            crop_path = row_get(row, "crop_path", "CropPath")
            if corner and layer == "L2" and axis and crop_path:
                val, sig = compute_alignment(anl, Path(crop_path), axis, verbose)
                if val is not None:
                    key = f"{corner}_L2_{axis}"
                    panel_map_new.setdefault(panel, {}).setdefault(key, []).append(
                        (val, sig if sig is not None else math.nan)
                    )


def panel_rows(panel_map_new, panel_map_old):
    rows = []
    all_panels = sorted(set(panel_map_new) | set(panel_map_old))
    for panel in all_panels:
        r = {"Panel ID": panel}
        new_vals, new_sigs = {}, {}
        for k in MEAS_ORDER:
            vals = panel_map_new.get(panel, {}).get(k, [])
            if vals:
                new_vals[k] = median(v for v, _ in vals)
                finite_sigs = [s for _, s in vals if math.isfinite(s)]
                new_sigs[k] = median(finite_sigs) if finite_sigs else None
            else:
                new_vals[k] = None
                new_sigs[k] = None
            r[k] = f"{new_vals[k]:.6f}" if new_vals[k] is not None else ""
            r[f"SIG_{k}"] = f"{new_sigs[k]:.6f}" if new_sigs[k] is not None else ""

        old = panel_map_old.get(panel, {})
        for k in MEAS_ORDER:
            # prefer axis-matched AOI value; only fall back to legacy scalar if needed
            corner = k.split("_", 1)[0]
            ov = old.get(k)
            if ov is None:
                ov = old.get(f"{corner}_L2")
            r[f"CDO_{k}"] = f"{ov:.6f}" if isinstance(ov, (int, float)) else ""

        for k in MEAS_ORDER:
            corner = k.split("_", 1)[0]
            n = new_vals[k]
            o = panel_map_old.get(panel, {}).get(k)
            if o is None:
                o = panel_map_old.get(panel, {}).get(f"{corner}_L2")
            r[f"DIFF_{k}"] = (
                f"{(n - o):.6f}"
                if n is not None and isinstance(o, (int, float))
                else ""
            )
        rows.append(r)
    return rows


def write_rows(csv_path: Path, rows):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_HEADER)
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ============================================================
# Main
# ============================================================
def main():
    ap = argparse.ArgumentParser(description="Lean panel overlay aggregate (YOLO vs AOI) [axis fix]")
    ap.add_argument("--config", default=None)
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    cfg = load_cfg(args.config)
    out_root = Path(_get(cfg, "paths", "out_root")).expanduser()
    analyzer = Path(_get(cfg, "paths", "analyzer")).expanduser()
    csv_path = Path(_get(cfg, "paths", "panel_csv")).expanduser()

    anl = import_analyzer(analyzer)
    manifests = read_manifests(out_root)
    panel_map_new = {}
    panel_map_old = {}

    for m in manifests:
        aggregate_from_manifest(m, anl, panel_map_new, panel_map_old, args.verbose)

    rows = panel_rows(panel_map_new, panel_map_old)
    write_rows(csv_path, rows)
    print(f"[DONE] Wrote {len(rows)} panels → {csv_path}")


if __name__ == "__main__":
    main()
