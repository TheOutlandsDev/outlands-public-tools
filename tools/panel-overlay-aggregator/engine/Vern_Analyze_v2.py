"""
Robust PNG Vernier Group Offset Tool (Rev 3b)

What this script does
---------------------
1) Opens a PNG microscope image
2) Extracts 10 blue and 10 green line profiles
3) Interpolates each profile to a finer grid
4) Finds local minima (etched valleys)
5) Finds local maxima between paired minima (bar centers)
6) Computes the center of the BLUE bar grouping
7) Computes the center of the GREEN bar grouping
8) Reports:
      Green - Blue Group Offset
   in:
      - verniers
      - micrometers
      - original pixels
      - interpolated pixels

No-display mode
---------------
If you run:
    python Vern_Analyze_v2.py --no-display

the script prints ONLY:
    <offset_in_verniers> <error_in_verniers>

Example:
    0.123456 0.018732

The first number is Green - Blue Group Offset in verniers.
The second number is the estimated 1-sigma uncertainty in verniers.

Notes
-----
- One vernier = one bar-center-to-adjacent-bar-center spacing
- The spacing between bar centers is assumed to be exactly 10 um
- Bar width is NOT used because etch changes width
- The grouping center is the median of the detected black-dot bar centers
- The uncertainty is estimated from the spread of per-line grouping centers
"""

from __future__ import annotations
import argparse
import sys
import tkinter as tk
from tkinter import filedialog

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt


# ----------------------
# USER CONFIGURATION
# ----------------------
LANDSCAPE_ROWS_GROUP_A = range(20, 40, 2)   # 10 blue rows
LANDSCAPE_ROWS_GROUP_B = range(60, 80, 2)   # 10 green rows

PORTRAIT_COLS_GROUP_A = range(8, 28, 2)    # Rev 3b: shifted right by +3 px
PORTRAIT_COLS_GROUP_B = range(53, 73, 2)    # Rev 3b: shifted right by +3 px

MINIMA_THRESHOLD = 200.0
WINDOW_RADIUS = 3
MIN_SEPARATION = 3

TARGET_MINIMA = 22
TARGET_CENTERS = TARGET_MINIMA // 2   # 11 centers

CENTER_START_UM = 100.0
CENTER_STEP_UM = 10.0

INTERP_LEN = 2280
SUBPIXEL_HALF_WINDOW = 2

MAD_SCALE = 3.0
MIN_ABS_RESIDUAL_UM = 0.50
MIN_INLIERS = 6

# Rev 3b QC / gating configuration
REV3B_CANDIDATE_MARGIN = 4
REV3B_MIN_BAND_COUNT = 8
REV3B_MIN_CONTRAST = 10.0
REV3B_CENTER_TOL_FRAC = 0.18
REV3B_SPACING_MAD_FRAC = 0.25
REV3B_MIN_VALID_LINES = 8
REV3B_MAX_VALID_LINES = 14


# ----------------------
# Utilities
# ----------------------
def select_png_file() -> str:
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    path = filedialog.askopenfilename(
        title="Select a PNG file",
        filetypes=[("PNG files", "*.png"), ("All files", "*.*")],
    )
    root.destroy()
    return path or ""


def load_image_as_arrays(path: str):
    img = Image.open(path)
    rgb = np.array(img.convert("RGB"))
    gray = np.array(img.convert("L"), dtype=np.float64)
    return rgb, gray


def orientation_from_shape(gray_arr: np.ndarray) -> str:
    h, w = gray_arr.shape
    return "landscape" if w >= h else "portrait"


def validate_indices(indices, max_allowed: int):
    return [int(i) for i in indices if 0 <= int(i) < max_allowed]


def normalize_to_1000(signal: np.ndarray) -> np.ndarray:
    shifted = signal - np.min(signal)
    mx = np.max(shifted)
    if mx < 1e-12:
        return np.zeros_like(signal, dtype=np.float64)
    return (shifted / mx) * 1000.0


def interp_profile(signal: np.ndarray, out_len: int = INTERP_LEN) -> np.ndarray:
    signal = np.asarray(signal, dtype=np.float64)
    n = signal.size
    if n < 2:
        return np.full(out_len, signal[0] if n == 1 else 0.0, dtype=np.float64)

    x_old = np.arange(n, dtype=np.float64)
    x_new = np.linspace(0, n - 1, out_len)
    return np.interp(x_new, x_old, signal)


def intensity_at_x(profile: np.ndarray, x_vals: np.ndarray) -> np.ndarray:
    x_vals = np.asarray(x_vals, dtype=np.float64)
    x_old = np.arange(profile.size, dtype=np.float64)
    return np.interp(x_vals, x_old, profile)


def robust_median(values: np.ndarray) -> float:
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return np.nan
    return float(np.median(values))


def robust_sigma(values: np.ndarray) -> float:
    """
    Robust estimate of 1-sigma using MAD.
    sigma ~= 1.4826 * MAD
    """
    values = np.asarray(values, dtype=np.float64)
    values = values[np.isfinite(values)]
    if values.size < 2:
        return np.nan
    med = np.median(values)
    mad = np.median(np.abs(values - med))
    return float(1.4826 * mad)


def show_image_with_lines(
    rgb_arr: np.ndarray,
    orientation: str,
    group_a: list[int],
    group_b: list[int],
    title="Image with sampling lines",
):
    h, w, _ = rgb_arr.shape
    plt.figure()
    plt.imshow(rgb_arr)

    if orientation == "landscape":
        for y in group_a:
            plt.hlines(y, 0, w - 1, colors="b", linestyles="-", linewidth=1)
        for y in group_b:
            plt.hlines(y, 0, w - 1, colors="g", linestyles="-", linewidth=1)
    else:
        for x in group_a:
            plt.vlines(x, 0, h - 1, colors="b", linestyles="-", linewidth=1)
        for x in group_b:
            plt.vlines(x, 0, h - 1, colors="g", linestyles="-", linewidth=1)

    plt.title(title)
    plt.axis("off")
    plt.tight_layout()


# ----------------------
# Extrema detection
# ----------------------
def find_local_minima_indices(
    signal: np.ndarray,
    threshold: float = MINIMA_THRESHOLD,
    window_radius: int = WINDOW_RADIUS,
    target_count: int = TARGET_MINIMA,
    min_separation: int | None = None,
) -> np.ndarray:
    s = np.asarray(signal, dtype=np.float64)
    n = s.size
    r = int(max(1, window_radius))
    if min_separation is None:
        min_separation = r

    def pick_with_threshold(thresh: float) -> np.ndarray:
        candidates = []
        for i in range(n):
            if s[i] < thresh:
                lo = max(0, i - r)
                hi = min(n, i + r + 1)
                win = s[lo:hi]
                if s[i] == np.min(win):
                    candidates.append(i)

        if not candidates:
            return np.array([], dtype=int)

        candidates = np.array(candidates, dtype=int)
        order = np.argsort(s[candidates])
        candidates_sorted = candidates[order]

        picked = []
        for idx in candidates_sorted:
            if all(abs(idx - p) >= min_separation for p in picked):
                picked.append(int(idx))
            if len(picked) >= target_count:
                break

        return np.array(sorted(picked), dtype=int)

    picked = pick_with_threshold(float(threshold))

    if picked.size < target_count:
        for extra in (25.0, 50.0, 100.0, 200.0):
            picked = pick_with_threshold(float(threshold + extra))
            if picked.size >= target_count:
                break

    if picked.size > target_count:
        order = np.argsort(s[picked])
        picked = picked[order][:target_count]
        picked = np.array(sorted(picked), dtype=int)

    return picked


def refine_extremum_quadratic(signal: np.ndarray, idx: int, kind: str, half_window: int = SUBPIXEL_HALF_WINDOW) -> float:
    s = np.asarray(signal, dtype=np.float64)
    n = s.size

    lo = max(0, idx - half_window)
    hi = min(n, idx + half_window + 1)

    x = np.arange(lo, hi, dtype=np.float64)
    y = s[lo:hi]

    if x.size < 3:
        return float(idx)

    try:
        a, b, c = np.polyfit(x, y, 2)
        if abs(a) < 1e-15:
            return float(idx)

        x_vertex = -b / (2.0 * a)
        x_vertex = min(max(x_vertex, float(lo)), float(hi - 1))

        if kind == "min" and a <= 0:
            return float(idx)
        if kind == "max" and a >= 0:
            return float(idx)

        return float(x_vertex)
    except Exception:
        return float(idx)


def detect_refined_minima(signal: np.ndarray) -> np.ndarray:
    mins = find_local_minima_indices(
        signal,
        threshold=MINIMA_THRESHOLD,
        window_radius=WINDOW_RADIUS,
        target_count=TARGET_MINIMA,
        min_separation=MIN_SEPARATION,
    )
    if mins.size == 0:
        return np.array([], dtype=float)

    refined = np.array([refine_extremum_quadratic(signal, int(i), kind="min") for i in mins], dtype=float)
    refined.sort()
    return refined


def maxima_between_minima_refined(signal: np.ndarray, minima_x: np.ndarray) -> np.ndarray:
    s = np.asarray(signal, dtype=np.float64)
    mins = np.asarray(minima_x, dtype=np.float64)

    if mins.size < 2:
        return np.array([], dtype=float)

    if mins.size % 2 != 0:
        mins = mins[:-1]

    centers = []
    for i in range(0, mins.size, 2):
        a = mins[i]
        b = mins[i + 1]

        lo = int(np.floor(min(a, b)))
        hi = int(np.ceil(max(a, b)))

        if hi <= lo + 1:
            centers.append((a + b) / 2.0)
            continue

        seg = s[lo:hi + 1]
        j = int(np.argmax(seg))
        idx_max = lo + j
        x_refined = refine_extremum_quadratic(s, idx_max, kind="max")
        centers.append(x_refined)

    return np.array(centers, dtype=float)


# ----------------------
# Robust line fitting
# ----------------------
def ordinary_least_squares_line(x: np.ndarray, y: np.ndarray):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)
    if x.size < 2 or y.size < 2 or x.size != y.size:
        return None
    m, b = np.polyfit(x, y, 1)
    return float(m), float(b)


def theil_sen_line(x: np.ndarray, y: np.ndarray):
    x = np.asarray(x, dtype=np.float64)
    y = np.asarray(y, dtype=np.float64)

    if x.size < 2 or y.size < 2 or x.size != y.size:
        return None

    slopes = []
    n = x.size
    for i in range(n):
        for j in range(i + 1, n):
            dx = x[j] - x[i]
            if abs(dx) > 1e-12:
                slopes.append((y[j] - y[i]) / dx)

    if not slopes:
        return None

    m = float(np.median(slopes))
    b = float(np.median(y - m * x))
    return m, b


def line_stats(x: np.ndarray, y: np.ndarray, m: float, b: float):
    y_fit = m * x + b
    resid = y - y_fit

    ss_res = np.sum(resid ** 2)
    ss_tot = np.sum((y - np.mean(y)) ** 2)
    r2 = np.nan if ss_tot < 1e-12 else 1.0 - (ss_res / ss_tot)
    rmse = np.sqrt(np.mean(resid ** 2))
    mad = np.median(np.abs(resid - np.median(resid)))

    return {
        "y_fit": y_fit,
        "residuals": resid,
        "r2": float(r2) if not np.isnan(r2) else np.nan,
        "rmse_um": float(rmse),
        "mad_um": float(mad),
    }


def robust_fit_known_centers(x_pixels: np.ndarray, y_um: np.ndarray):
    x = np.asarray(x_pixels, dtype=np.float64)
    y = np.asarray(y_um, dtype=np.float64)

    if x.size < 2 or x.size != y.size:
        return None

    init = theil_sen_line(x, y)
    if init is None:
        return None

    m0, b0 = init
    stats0 = line_stats(x, y, m0, b0)
    resid0 = stats0["residuals"]
    mad0 = stats0["mad_um"]

    thresh = max(MIN_ABS_RESIDUAL_UM, MAD_SCALE * max(mad0, 1e-12))
    inliers = np.abs(resid0 - np.median(resid0)) <= thresh

    if np.count_nonzero(inliers) < max(2, MIN_INLIERS):
        m, b = m0, b0
        stats = line_stats(x, y, m, b)
        return {
            "slope_um_per_interp": float(m),
            "intercept_um": float(b),
            "stats_all": stats,
            "stats_inliers": stats,
            "inlier_mask": np.ones_like(x, dtype=bool),
            "n_points": int(x.size),
            "n_inliers": int(x.size),
            "equation": f"um = {m:.6f}*x + {b:.6f}",
        }

    fit_ls = ordinary_least_squares_line(x[inliers], y[inliers])
    if fit_ls is None:
        m, b = m0, b0
    else:
        m, b = fit_ls

    stats_all = line_stats(x, y, m, b)
    stats_in = line_stats(x[inliers], y[inliers], m, b)

    return {
        "slope_um_per_interp": float(m),
        "intercept_um": float(b),
        "stats_all": stats_all,
        "stats_inliers": stats_in,
        "inlier_mask": inliers,
        "n_points": int(x.size),
        "n_inliers": int(np.count_nonzero(inliers)),
        "equation": f"um = {m:.6f}*x + {b:.6f}",
    }


def summarize_fit_stats(fits: list[dict]) -> dict:
    valid = [f for f in fits if f is not None]
    if not valid:
        return {}

    slopes = np.array([f["slope_um_per_interp"] for f in valid], dtype=float)
    intercepts = np.array([f["intercept_um"] for f in valid], dtype=float)
    r2s = np.array([f["stats_inliers"]["r2"] for f in valid], dtype=float)
    rmses = np.array([f["stats_inliers"]["rmse_um"] for f in valid], dtype=float)
    nin = np.array([f["n_inliers"] for f in valid], dtype=float)

    return {
        "n": len(valid),
        "slope_median": float(np.median(slopes)),
        "intercept_median": float(np.median(intercepts)),
        "r2_median": float(np.nanmedian(r2s)),
        "rmse_median": float(np.median(rmses)),
        "n_inliers_median": float(np.median(nin)),
    }


# ----------------------
# Plot helpers
# ----------------------
def plot_profile_family_with_dots(
    profiles: list[np.ndarray],
    color: str,
    title: str,
    xlabel: str,
    median_minima_x: np.ndarray,
    median_centers_x: np.ndarray,
    group_center_x: float,
    show_plots: bool = True,
):
    if not show_plots:
        return

    axis = np.arange(INTERP_LEN)
    plt.figure()

    for prof in profiles:
        plt.plot(axis, prof, color=color, alpha=0.65, linewidth=1)

    if profiles:
        median_profile = np.median(np.vstack(profiles), axis=0)

        if median_minima_x.size:
            y_red = intensity_at_x(median_profile, median_minima_x)
            plt.scatter(median_minima_x, y_red, color="r", s=38, zorder=5, label="Minima")

        if median_centers_x.size:
            y_blk = intensity_at_x(median_profile, median_centers_x)
            plt.scatter(median_centers_x, y_blk, color="k", s=38, zorder=6, label="Centers")

        if np.isfinite(group_center_x):
            y_gc = float(intensity_at_x(median_profile, np.array([group_center_x]))[0])
            plt.scatter([group_center_x], [y_gc], color="m", s=70, zorder=7, label="Group center")
            plt.axvline(group_center_x, color="m", linestyle="--", linewidth=1)

        if median_minima_x.size or median_centers_x.size or np.isfinite(group_center_x):
            plt.legend()

    plt.xlabel(xlabel)
    plt.ylabel("intensity (0..255)")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.tight_layout()


def plot_fit_family(
    x_sets: list[np.ndarray],
    y_sets: list[np.ndarray],
    fit_results: list[dict],
    color: str,
    title: str,
    stats_text: str,
    summary_equation: str,
    show_plots: bool = True,
):
    if not show_plots:
        return

    plt.figure()
    x_all_valid = []

    for x, y, fit in zip(x_sets, y_sets, fit_results):
        if fit is None or x.size < 2:
            continue

        inliers = fit["inlier_mask"]
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)

        outliers = ~inliers
        if np.any(outliers):
            plt.scatter(x[outliers], y[outliers], marker="x", s=35, color="r", alpha=0.8)

        plt.scatter(x[inliers], y[inliers], color=color, s=18, alpha=0.75)

        x_line = np.linspace(np.min(x), np.max(x), 200)
        y_line = fit["slope_um_per_interp"] * x_line + fit["intercept_um"]
        plt.plot(x_line, y_line, color=color, alpha=0.35, linewidth=1.2)
        x_all_valid.append(x)

    plt.xlabel("interpolated pixel index")
    plt.ylabel("position (µm)")
    plt.title(title)
    plt.grid(True, alpha=0.3)

    if x_all_valid:
        x_cat = np.concatenate(x_all_valid)
        x_line = np.linspace(np.min(x_cat), np.max(x_cat), 300)
        parts = summary_equation.replace("um = ", "").replace("*x + ", ",").split(",")
        if len(parts) == 2:
            try:
                m_med = float(parts[0])
                b_med = float(parts[1])
                y_line = m_med * x_line + b_med
                plt.plot(x_line, y_line, linewidth=2.5, color="k")
            except Exception:
                pass

    ax = plt.gca()
    ax.text(
        0.02,
        0.98,
        summary_equation + "\n" + stats_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        bbox=dict(boxstyle="round", facecolor="white", alpha=0.88),
    )

    plt.tight_layout()


def plot_group_center_summary(blue_centers_x, green_centers_x, blue_group_center, green_group_center, show_plots=True):
    if not show_plots:
        return

    plt.figure()

    if blue_centers_x.size:
        yb = np.zeros_like(blue_centers_x, dtype=float)
        plt.scatter(blue_centers_x, yb, color="b", s=40, label="Blue centers")
        plt.axvline(blue_group_center, color="b", linestyle="--", linewidth=2, label="Blue group center")

    if green_centers_x.size:
        yg = np.ones_like(green_centers_x, dtype=float)
        plt.scatter(green_centers_x, yg, color="g", s=40, label="Green centers")
        plt.axvline(green_group_center, color="g", linestyle="--", linewidth=2, label="Green group center")

    plt.yticks([0, 1], ["Blue", "Green"])
    plt.xlabel("interpolated pixel index")
    plt.title("Blue and Green group centers")
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()


# ----------------------
# Per-family processing
# ----------------------
def process_profile_family(
    interp_profiles: list[np.ndarray],
    color_label: str,
    color_code: str,
    xlabel: str,
    original_axis_len: int,
    show_plots: bool = True,
):
    known_center_um = CENTER_START_UM + CENTER_STEP_UM * np.arange(TARGET_CENTERS, dtype=float)

    minima_sets = []
    center_sets = []
    y_known_sets = []
    fit_results = []
    x_fit_sets = []

    per_line_center_spacing_interp = []
    per_line_group_centers = []

    for prof in interp_profiles:
        prof_norm = normalize_to_1000(prof)

        minima_x = detect_refined_minima(prof_norm)
        center_x = maxima_between_minima_refined(prof_norm, minima_x)

        n_cent = min(TARGET_CENTERS, center_x.size)
        center_x = center_x[:n_cent]
        y_um = known_center_um[:n_cent]

        minima_sets.append(minima_x)
        center_sets.append(center_x)
        y_known_sets.append(y_um)

        if center_x.size >= 2:
            spacings = np.diff(center_x)
            per_line_center_spacing_interp.append(float(np.median(spacings)))
            per_line_group_centers.append(float(np.median(center_x)))

        if center_x.size < 2:
            fit_results.append(None)
            x_fit_sets.append(np.array([], dtype=float))
            continue

        fit = robust_fit_known_centers(center_x, y_um)
        fit_results.append(fit)

        if fit is None:
            x_fit_sets.append(np.array([], dtype=float))
        else:
            m = fit["slope_um_per_interp"]
            b = fit["intercept_um"]
            x_fit = (y_um - b) / m
            x_fit_sets.append(x_fit)

    valid_min_sets = [x for x in minima_sets if x.size > 0]
    if valid_min_sets:
        n_common_min = min(len(x) for x in valid_min_sets)
        min_stack = np.vstack([x[:n_common_min] for x in valid_min_sets])
        median_minima_x = np.median(min_stack, axis=0)
    else:
        median_minima_x = np.array([], dtype=float)

    valid_center_sets = [x for x in center_sets if x.size > 0]
    if valid_center_sets:
        n_common_cent = min(len(x) for x in valid_center_sets)
        cent_stack = np.vstack([x[:n_common_cent] for x in valid_center_sets])
        median_centers_x = np.median(cent_stack, axis=0)
    else:
        median_centers_x = np.array([], dtype=float)

    valid_xfit = [x for x in x_fit_sets if x.size > 0]
    if valid_xfit:
        n_common_fit = min(len(x) for x in valid_xfit)
        xfit_stack = np.vstack([x[:n_common_fit] for x in valid_xfit])
        median_fitted_centers_x = np.median(xfit_stack, axis=0)
        known_center_um_common = known_center_um[:n_common_fit]
    else:
        median_fitted_centers_x = np.array([], dtype=float)
        known_center_um_common = np.array([], dtype=float)

    stats = summarize_fit_stats(fit_results)

    interp_scale = INTERP_LEN / float(original_axis_len)
    slope_med_interp = stats.get("slope_median", np.nan)
    slope_med_orig_px = slope_med_interp * interp_scale if not np.isnan(slope_med_interp) else np.nan
    intercept_med = stats.get("intercept_median", np.nan)

    summary_equation = f"um = {slope_med_interp:.6f}*x + {intercept_med:.6f}"

    median_spacing_interp = robust_median(np.array(per_line_center_spacing_interp, dtype=float))
    median_group_center_interp = robust_median(np.array(per_line_group_centers, dtype=float))

    if median_fitted_centers_x.size:
        median_group_center_interp = float(np.median(median_fitted_centers_x))
    elif median_centers_x.size:
        median_group_center_interp = float(np.median(median_centers_x))

    median_spacing_orig_px = median_spacing_interp / interp_scale if np.isfinite(median_spacing_interp) else np.nan
    um_per_interp = 10.0 / median_spacing_interp if np.isfinite(median_spacing_interp) and abs(median_spacing_interp) > 1e-12 else np.nan
    um_per_orig_px = 10.0 / median_spacing_orig_px if np.isfinite(median_spacing_orig_px) and abs(median_spacing_orig_px) > 1e-12 else np.nan

    # Uncertainty on family group center from per-line group-center spread
    group_center_sigma_interp = robust_sigma(np.array(per_line_group_centers, dtype=float))
    n_group = len(per_line_group_centers)
    group_center_sem_interp = group_center_sigma_interp / np.sqrt(n_group) if n_group > 0 and np.isfinite(group_center_sigma_interp) else np.nan

    stats_text = (
        f"median slope = {slope_med_interp:.6f} µm/interp\n"
        f"median slope = {slope_med_orig_px:.6f} µm/orig-px\n"
        f"median intercept = {intercept_med:.6f} µm\n"
        f"median R² = {stats.get('r2_median', np.nan):.6f}\n"
        f"median RMSE = {stats.get('rmse_median', np.nan):.6f} µm\n"
        f"valid fits = {stats.get('n', 0)}\n"
        f"median inliers = {stats.get('n_inliers_median', np.nan):.1f}\n"
        f"interp px / vernier = {median_spacing_interp:.6f}"
    )

    plot_profile_family_with_dots(
        profiles=interp_profiles,
        color=color_code,
        title=f"{color_label} interpolated profiles + median red minima + median black centers",
        xlabel=xlabel,
        median_minima_x=median_minima_x,
        median_centers_x=median_fitted_centers_x if median_fitted_centers_x.size else median_centers_x,
        group_center_x=median_group_center_interp,
        show_plots=show_plots,
    )

    plot_fit_family(
        x_sets=center_sets,
        y_sets=y_known_sets,
        fit_results=fit_results,
        color=color_code,
        title=f"{color_label} robust center fits",
        stats_text=stats_text,
        summary_equation=summary_equation,
        show_plots=show_plots,
    )

    return {
        "minima_sets": minima_sets,
        "center_sets": center_sets,
        "y_known_sets": y_known_sets,
        "fit_results": fit_results,
        "x_fit_sets": x_fit_sets,
        "median_minima_x": median_minima_x,
        "median_centers_x": median_centers_x,
        "median_fitted_centers_x": median_fitted_centers_x,
        "known_center_um_common": known_center_um_common,
        "stats": stats,
        "summary_equation": summary_equation,
        "group_center_interp": median_group_center_interp,
        "pixels_per_vernier_interp": median_spacing_interp,
        "pixels_per_vernier_orig_px": median_spacing_orig_px,
        "um_per_interp": um_per_interp,
        "um_per_orig_px": um_per_orig_px,
        "group_center_sigma_interp": group_center_sigma_interp,
        "group_center_sem_interp": group_center_sem_interp,
        "per_line_group_centers": np.array(per_line_group_centers, dtype=float),
    }


# ----------------------
# Main plotting + analysis routine
# ----------------------
def plot_profiles_and_compute_alignment(
    gray_arr: np.ndarray,
    rgb_arr: np.ndarray,
    orientation: str,
    group_a: list[int],
    group_b: list[int],
    show_plots: bool = True,
):
    h, w = gray_arr.shape

    if orientation == "landscape":
        raw_profiles_blue = [gray_arr[y, :] for y in group_a] if group_a else []
        raw_profiles_green = [gray_arr[y, :] for y in group_b] if group_b else []
        xlabel = "x (interpolated index)"
        orig_axis_len = w
    else:
        raw_profiles_blue = [gray_arr[:, x] for x in group_a] if group_a else []
        raw_profiles_green = [gray_arr[:, x] for x in group_b] if group_b else []
        xlabel = "y (interpolated index)"
        orig_axis_len = h

    if not raw_profiles_blue or not raw_profiles_green:
        raise RuntimeError("Both Group A and Group B must be present.")

    interp_profiles_blue = [interp_profile(p, out_len=INTERP_LEN) for p in raw_profiles_blue]
    interp_profiles_green = [interp_profile(p, out_len=INTERP_LEN) for p in raw_profiles_green]

    if show_plots:
        show_image_with_lines(
            rgb_arr,
            orientation,
            group_a,
            group_b,
            title="Image with sampling lines (blue=Group A, green=Group B)"
        )

    blue_results = process_profile_family(
        interp_profiles=interp_profiles_blue,
        color_label="Blue",
        color_code="b",
        xlabel=xlabel,
        original_axis_len=orig_axis_len,
        show_plots=show_plots,
    )

    green_results = process_profile_family(
        interp_profiles=interp_profiles_green,
        color_label="Green",
        color_code="g",
        xlabel=xlabel,
        original_axis_len=orig_axis_len,
        show_plots=show_plots,
    )

    blue_group_center_interp = blue_results["group_center_interp"]
    green_group_center_interp = green_results["group_center_interp"]

    delta_interp = green_group_center_interp - blue_group_center_interp

    interp_scale = INTERP_LEN / float(orig_axis_len)
    delta_orig_px = delta_interp / interp_scale if np.isfinite(delta_interp) else np.nan

    ppv_blue = blue_results["pixels_per_vernier_interp"]
    ppv_green = green_results["pixels_per_vernier_interp"]
    ppv_interp = robust_median(np.array([ppv_blue, ppv_green], dtype=float))

    ppv_blue_orig = blue_results["pixels_per_vernier_orig_px"]
    ppv_green_orig = green_results["pixels_per_vernier_orig_px"]
    ppv_orig_px = robust_median(np.array([ppv_blue_orig, ppv_green_orig], dtype=float))

    delta_verniers = delta_interp / ppv_interp if np.isfinite(delta_interp) and np.isfinite(ppv_interp) and abs(ppv_interp) > 1e-12 else np.nan
    delta_um = delta_verniers * 10.0 if np.isfinite(delta_verniers) else np.nan

    # Error estimate:
    # family group-center uncertainty from per-line spread, propagated in quadrature
    sem_blue_interp = blue_results["group_center_sem_interp"]
    sem_green_interp = green_results["group_center_sem_interp"]
    delta_sem_interp = np.sqrt(sem_blue_interp**2 + sem_green_interp**2) if np.isfinite(sem_blue_interp) and np.isfinite(sem_green_interp) else np.nan

    delta_sem_orig_px = delta_sem_interp / interp_scale if np.isfinite(delta_sem_interp) else np.nan
    delta_sem_verniers = delta_sem_interp / ppv_interp if np.isfinite(delta_sem_interp) and np.isfinite(ppv_interp) and abs(ppv_interp) > 1e-12 else np.nan
    delta_sem_um = delta_sem_verniers * 10.0 if np.isfinite(delta_sem_verniers) else np.nan

    plot_group_center_summary(
        blue_results["median_fitted_centers_x"] if blue_results["median_fitted_centers_x"].size else blue_results["median_centers_x"],
        green_results["median_fitted_centers_x"] if green_results["median_fitted_centers_x"].size else green_results["median_centers_x"],
        blue_group_center_interp,
        green_group_center_interp,
        show_plots=show_plots,
    )

    return {
        "xlabel": xlabel,
        "blue_results": blue_results,
        "green_results": green_results,
        "delta_interp": delta_interp,
        "delta_orig_px": delta_orig_px,
        "delta_verniers": delta_verniers,
        "delta_um": delta_um,
        "delta_sem_interp": delta_sem_interp,
        "delta_sem_orig_px": delta_sem_orig_px,
        "delta_sem_verniers": delta_sem_verniers,
        "delta_sem_um": delta_sem_um,
        "pixels_per_vernier_interp": ppv_interp,
        "pixels_per_vernier_orig_px": ppv_orig_px,
    }



# ----------------------
# Rev 3b: expanded sampling + per-line QC gating before measurement math
# ----------------------
def rev3b_expand_sampling_indices(base_indices, max_allowed: int, margin: int = REV3B_CANDIDATE_MARGIN) -> list[int]:
    valid = validate_indices(base_indices, max_allowed)
    if not valid:
        return []
    lo = max(0, min(valid) - int(margin))
    hi = min(max_allowed - 1, max(valid) + int(margin))
    return list(range(lo, hi + 1))


def rev3b_smooth_1d(signal: np.ndarray, window: int = 7) -> np.ndarray:
    s = np.asarray(signal, dtype=np.float64)
    if s.size == 0 or window <= 1:
        return s.copy()
    kernel = np.ones(int(window), dtype=np.float64) / float(window)
    return np.convolve(s, kernel, mode='same')


def rev3b_dark_runs_1d(signal: np.ndarray, threshold_rel: float = 0.35, min_run: int = 2):
    s = np.asarray(signal, dtype=np.float64)
    if s.size == 0:
        return []
    darkness = np.max(s) - s
    darkness = rev3b_smooth_1d(darkness, window=5)
    peak = float(np.max(darkness))
    if peak < 1e-12:
        return []
    thresh = float(threshold_rel) * peak
    mask = darkness >= thresh
    runs = []
    start = None
    for i, flag in enumerate(mask):
        if flag and start is None:
            start = i
        elif (not flag) and start is not None:
            if i - start >= min_run:
                runs.append((start, i - 1))
            start = None
    if start is not None and len(mask) - start >= min_run:
        runs.append((start, len(mask) - 1))
    return runs


def rev3b_profile_qc(profile: np.ndarray) -> dict:
    s = np.asarray(profile, dtype=np.float64)
    if s.size == 0:
        return {
            'contrast': 0.0,
            'band_count': 0,
            'median_spacing': np.nan,
            'spacing_mad': np.nan,
            'centers': np.array([], dtype=np.float64),
            'runs': [],
        }
    contrast = float(np.percentile(s, 95) - np.percentile(s, 5))
    runs = rev3b_dark_runs_1d(s, threshold_rel=0.35, min_run=2)
    centers = np.array([(a + b) / 2.0 for a, b in runs], dtype=np.float64) if runs else np.array([], dtype=np.float64)
    if centers.size >= 2:
        spacings = np.diff(centers)
        median_spacing = float(np.median(spacings))
        spacing_mad = float(np.median(np.abs(spacings - median_spacing)))
    else:
        median_spacing = np.nan
        spacing_mad = np.nan
    return {
        'contrast': contrast,
        'band_count': int(centers.size),
        'median_spacing': median_spacing,
        'spacing_mad': spacing_mad,
        'centers': centers,
        'runs': runs,
    }


def rev3b_estimate_comb_center(gray_arr: np.ndarray, orientation: str, candidate_indices: list[int]) -> tuple[float, float]:
    if not candidate_indices:
        return np.nan, np.nan
    h, w = gray_arr.shape
    if orientation == 'portrait':
        x0 = max(0, min(candidate_indices))
        x1 = min(w - 1, max(candidate_indices))
        crop = gray_arr[:, x0:x1 + 1]
        if crop.size == 0:
            return np.nan, np.nan
        proj = rev3b_smooth_1d((np.max(crop) - crop).mean(axis=0), window=7)
        peak = float(np.max(proj)) if proj.size else 0.0
        if peak < 1e-12:
            return float((x0 + x1) / 2.0), float(max(1.0, (x1 - x0) / 2.0))
        thresh = 0.30 * peak
        idx = np.flatnonzero(proj >= thresh)
        if idx.size == 0:
            return float((x0 + x1) / 2.0), float(max(1.0, (x1 - x0) / 2.0))
        left = float(x0 + idx[0])
        right = float(x0 + idx[-1])
        return float((left + right) / 2.0), float(max(1.0, right - left))
    else:
        y0 = max(0, min(candidate_indices))
        y1 = min(h - 1, max(candidate_indices))
        crop = gray_arr[y0:y1 + 1, :]
        if crop.size == 0:
            return np.nan, np.nan
        proj = rev3b_smooth_1d((np.max(crop) - crop).mean(axis=1), window=7)
        peak = float(np.max(proj)) if proj.size else 0.0
        if peak < 1e-12:
            return float((y0 + y1) / 2.0), float(max(1.0, (y1 - y0) / 2.0))
        thresh = 0.30 * peak
        idx = np.flatnonzero(proj >= thresh)
        if idx.size == 0:
            return float((y0 + y1) / 2.0), float(max(1.0, (y1 - y0) / 2.0))
        top = float(y0 + idx[0])
        bottom = float(y0 + idx[-1])
        return float((top + bottom) / 2.0), float(max(1.0, bottom - top))


def rev3b_gate_indices(gray_arr: np.ndarray, orientation: str, candidate_indices: list[int]) -> tuple[list[int], dict]:
    if not candidate_indices:
        return [], {'candidates': 0, 'kept': 0}
    comb_center, comb_span = rev3b_estimate_comb_center(gray_arr, orientation, candidate_indices)
    center_tol = max(1.5, REV3B_CENTER_TOL_FRAC * max(comb_span, 1.0))
    scored = []
    for idx in candidate_indices:
        profile = gray_arr[:, idx] if orientation == 'portrait' else gray_arr[idx, :]
        q = rev3b_profile_qc(profile)
        pos = float(idx)
        center_error = abs(pos - comb_center) if np.isfinite(comb_center) else 0.0
        spacing_ok = (
            q['band_count'] >= 2
            and np.isfinite(q['median_spacing'])
            and np.isfinite(q['spacing_mad'])
            and q['spacing_mad'] <= max(1.5, REV3B_SPACING_MAD_FRAC * max(q['median_spacing'], 1.0))
        )
        basic_ok = (
            q['band_count'] >= REV3B_MIN_BAND_COUNT
            and q['contrast'] >= REV3B_MIN_CONTRAST
            and center_error <= center_tol
        )
        keep = bool(basic_ok and spacing_ok)
        score = (
            min(q['band_count'], 20) * 10.0
            + min(q['contrast'], 80.0)
            - (center_error * 10.0)
            - (0.0 if not np.isfinite(q['spacing_mad']) else q['spacing_mad'] * 6.0)
        )
        scored.append({
            'idx': int(idx),
            'keep': keep,
            'score': float(score),
            'center_error': float(center_error),
            'band_count': int(q['band_count']),
            'contrast': float(q['contrast']),
            'median_spacing': float(q['median_spacing']) if np.isfinite(q['median_spacing']) else np.nan,
            'spacing_mad': float(q['spacing_mad']) if np.isfinite(q['spacing_mad']) else np.nan,
        })
    kept = [row['idx'] for row in scored if row['keep']]
    fallback_used = False
    if len(kept) < REV3B_MIN_VALID_LINES:
        ranked = sorted(scored, key=lambda row: row['score'], reverse=True)
        fallback_n = min(max(REV3B_MIN_VALID_LINES, len(kept)), min(REV3B_MAX_VALID_LINES, len(ranked)))
        kept = sorted([row['idx'] for row in ranked[:fallback_n]])
        fallback_used = True
    else:
        kept = sorted(kept)
        if len(kept) > REV3B_MAX_VALID_LINES:
            kept = kept[:REV3B_MAX_VALID_LINES]
    meta = {
        'candidates': int(len(candidate_indices)),
        'kept': int(len(kept)),
        'comb_center': float(comb_center) if np.isfinite(comb_center) else np.nan,
        'comb_span': float(comb_span) if np.isfinite(comb_span) else np.nan,
        'center_tol': float(center_tol),
        'fallback_used': bool(fallback_used),
        'candidate_indices': [int(i) for i in candidate_indices],
        'kept_indices': [int(i) for i in kept],
        'scored': scored,
    }
    return kept, meta


def rev3b_build_sampling_groups(gray_arr: np.ndarray, orientation: str, base_group_a: list[int], base_group_b: list[int]):
    h, w = gray_arr.shape
    max_allowed = w if orientation == 'portrait' else h
    cand_a = rev3b_expand_sampling_indices(base_group_a, max_allowed=max_allowed, margin=REV3B_CANDIDATE_MARGIN)
    cand_b = rev3b_expand_sampling_indices(base_group_b, max_allowed=max_allowed, margin=REV3B_CANDIDATE_MARGIN)
    group_a, meta_a = rev3b_gate_indices(gray_arr, orientation, cand_a)
    group_b, meta_b = rev3b_gate_indices(gray_arr, orientation, cand_b)
    return group_a, group_b, {'group_a': meta_a, 'group_b': meta_b}


def print_rev3b_qc_summary(meta: dict):
    print("\nREV 3B LINE QC SUMMARY")
    for name, label in (("group_a", "Blue / Group A"), ("group_b", "Green / Group B")):
        row = meta.get(name, {})
        print(
            f"{label}: candidates={row.get('candidates', 0)}, kept={row.get('kept', 0)}, "
            f"center={row.get('comb_center', np.nan):.3f}, span={row.get('comb_span', np.nan):.3f}, "
            f"tol={row.get('center_tol', np.nan):.3f}, fallback_used={row.get('fallback_used', False)}"
        )
        print(f"  kept indices: {row.get('kept_indices', [])}")

# ----------------------
# CLI / main
# ----------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Robust PNG vernier grouping offset tool")
    ap.add_argument("--no-display", action="store_true", help="Do not display plots")
    args = ap.parse_args(argv)

    show_plots = not args.no_display

    path = select_png_file()
    if not path:
        if args.no_display:
            print("nan nan")
            return None
        print("No file selected.")
        return None

    rgb_arr, gray_arr = load_image_as_arrays(path)
    orient = orientation_from_shape(gray_arr)
    h, w = gray_arr.shape

    if orient == "landscape":
        base_group_a = validate_indices(LANDSCAPE_ROWS_GROUP_A, h)
        base_group_b = validate_indices(LANDSCAPE_ROWS_GROUP_B, h)
    else:
        base_group_a = validate_indices(PORTRAIT_COLS_GROUP_A, w)
        base_group_b = validate_indices(PORTRAIT_COLS_GROUP_B, w)

    if not base_group_a or not base_group_b:
        if args.no_display:
            print("nan nan")
            return None
        print("Need both Group A and Group B to compute alignment.")
        return None

    group_a, group_b, qc_meta = rev3b_build_sampling_groups(gray_arr, orient, base_group_a, base_group_b)
    if not group_a or not group_b:
        if args.no_display:
            print("nan nan")
            return None
        print("Rev 3b QC rejected all lines for at least one group.")
        return None
    if show_plots:
        print_rev3b_qc_summary(qc_meta)

    results = plot_profiles_and_compute_alignment(
        gray_arr,
        rgb_arr,
        orient,
        group_a,
        group_b,
        show_plots=show_plots,
    )

    if args.no_display:
        # ONLY print offset in verniers and its 1-sigma uncertainty
        val = results["delta_verniers"]
        err = results["delta_sem_verniers"]
        if not np.isfinite(val):
            val = np.nan
        if not np.isfinite(err):
            err = np.nan
        print(f"{val:.6f} {err:.6f}")
        return val

    print("\nBLUE SUMMARY")
    print(results["blue_results"]["summary_equation"])
    print(f"Blue group center: {results['blue_results']['group_center_interp']:.6f} interp")
    print(f"Blue interp px/vernier: {results['blue_results']['pixels_per_vernier_interp']:.6f}")
    print(f"Blue orig px/vernier: {results['blue_results']['pixels_per_vernier_orig_px']:.6f}")
    print(f"Blue um/interp px: {results['blue_results']['um_per_interp']:.9f}")

    print("\nGREEN SUMMARY")
    print(results["green_results"]["summary_equation"])
    print(f"Green group center: {results['green_results']['group_center_interp']:.6f} interp")
    print(f"Green interp px/vernier: {results['green_results']['pixels_per_vernier_interp']:.6f}")
    print(f"Green orig px/vernier: {results['green_results']['pixels_per_vernier_orig_px']:.6f}")
    print(f"Green um/interp px: {results['green_results']['um_per_interp']:.9f}")

    print("\nGREEN - BLUE GROUP OFFSET")
    print(f"Offset: {results['delta_interp']:.6f} interp pixels +/- {results['delta_sem_interp']:.6f}")
    print(f"Offset: {results['delta_orig_px']:.6f} original pixels +/- {results['delta_sem_orig_px']:.6f}")
    print(f"Offset: {results['delta_um']:.6f} um +/- {results['delta_sem_um']:.6f}")
    print(f"Offset: {results['delta_verniers']:.6f} verniers +/- {results['delta_sem_verniers']:.6f}")

    print("\nMEASURED SCALE")
    print(f"Measured interp pixels per vernier: {results['pixels_per_vernier_interp']:.6f}")
    print(f"Measured original pixels per vernier: {results['pixels_per_vernier_orig_px']:.6f}")

    if show_plots:
        plt.show()

    return results["delta_verniers"]


if __name__ == "__main__":
    val = main()
    if val is None:
        sys.exit(1)
    else:
        sys.exit(0)
