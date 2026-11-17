"""File-path adapter around the unchanged Rev 3b numerical implementation."""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import sys
import warnings

ROOT = Path(__file__).resolve().parent
MAX_BYTES = 16 * 1024 * 1024
MAX_PIXELS = 4_000_000


def ordinary(path, exists=True):
    path = Path(os.path.abspath(path))
    for part in (path, *path.parents):
        try:
            s = part.lstat()
        except FileNotFoundError:
            if part == path and not exists:
                continue
            raise ValueError('PATH_UNAVAILABLE') from None
        if stat.S_ISLNK(s.st_mode) or getattr(s, 'st_file_attributes', 0) & 0x400:
            raise ValueError('LINK_PATH_REFUSED')
    return path


def load_original():
    import matplotlib
    matplotlib.use('Agg', force=True)
    spec = importlib.util.spec_from_file_location('vernier_original_rev3b', ROOT / 'original/Vern_Analyze_v2.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def analyze(image, plots=None):
    path = ordinary(image)
    if not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise ValueError('INPUT_SIZE_OR_TYPE_REFUSED')
    output = ordinary(plots, False) if plots is not None else None
    if output is not None and os.path.lexists(output):
        raise ValueError('PLOT_DESTINATION_EXISTS')
    from PIL import Image
    # Validate and decode exactly one bounded PNG before invoking legacy code.
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(path) as im:
                if im.format != 'PNG' or getattr(im, 'n_frames', 1) != 1:
                    raise ValueError('SINGLE_PNG_REQUIRED')
                w, h = im.size
                if min(w, h) < 2 or w * h > MAX_PIXELS:
                    raise ValueError('IMAGE_DIMENSIONS_REFUSED')
                im.load()
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValueError('IMAGE_DIMENSIONS_REFUSED') from None
    m = load_original()
    try:
        rgb, gray = m.load_image_as_arrays(str(path))
        orient = m.orientation_from_shape(gray)
        a = m.LANDSCAPE_ROWS_GROUP_A if orient == 'landscape' else m.PORTRAIT_COLS_GROUP_A
        b = m.LANDSCAPE_ROWS_GROUP_B if orient == 'landscape' else m.PORTRAIT_COLS_GROUP_B
        bound = h if orient == 'landscape' else w
        a, b = m.validate_indices(a, bound), m.validate_indices(b, bound)
        if not a or not b:
            raise ValueError('SAMPLING_GROUPS_UNAVAILABLE')
        a, b, qc = m.rev3b_build_sampling_groups(gray, orient, a, b)
        # Legacy fallback also ranks blank lines. Refuse wholly featureless groups
        # in this adapter; never change the preserved legacy gate or ranking.
        for name in ('group_a', 'group_b'):
            selected = set(qc[name]['kept_indices'])
            if not any(r['idx'] in selected and r['contrast'] >= m.REV3B_MIN_CONTRAST and r['band_count'] >= m.REV3B_MIN_BAND_COUNT for r in qc[name]['scored']):
                raise ValueError('INSUFFICIENT_PATTERN')
        result = m.plot_profiles_and_compute_alignment(gray, rgb, orient, a, b, show_plots=output is not None)
        keys = ('delta_interp', 'delta_orig_px', 'delta_verniers', 'delta_um', 'delta_sem_interp', 'delta_sem_orig_px', 'delta_sem_verniers', 'delta_sem_um', 'pixels_per_vernier_interp', 'pixels_per_vernier_orig_px')
        numeric = {k: float(result[k]) for k in keys}
        if not all(math.isfinite(v) for v in numeric.values()) or numeric['pixels_per_vernier_interp'] <= 0:
            raise ValueError('NONFINITE_MEASUREMENT')
        fallback = any(qc[k]['fallback_used'] for k in ('group_a', 'group_b'))
        report = dict(schema=1, status='RESULT_REQUIRES_REVIEW', implementation='Rev 3b unchanged', orientation=orient,
                      dimensions=[w, h], results=numeric, fallback_used=fallback,
                      quality_approved=False, calibration_verified=False,
                      notes=['ASSUMED_10_UM_BAR_PITCH', 'SPREAD_ESTIMATE_IS_NOT_CALIBRATION', 'LEGACY_PIXEL_SCALE_USES_LENGTH_NOT_LENGTH_MINUS_ONE'] + (['QC_FALLBACK_RETAINED_FAILED_LINES'] if fallback else []),
                      groups={k: {f: qc[k][f] for f in ('candidates', 'kept', 'fallback_used', 'kept_indices')} for k in ('group_a', 'group_b')}, plots=[])
        if output is not None:
            output.mkdir()  # Exclusive new folder; never replace user files.
            for i, number in enumerate(m.plt.get_fignums(), 1):
                name = f'figure-{i:02d}.png'
                with (output / name).open('xb') as stream:
                    m.plt.figure(number).savefig(stream, format='png')
                report['plots'].append(name)
        return report
    finally:
        m.plt.close('all')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('image', type=Path, help='Explicit ordinary PNG file; no file picker')
    p.add_argument('--plots', type=Path, help='Create a NEW directory of rendered plots')
    args = p.parse_args(argv)
    try:
        value = analyze(args.image, args.plots)
    except (OSError, ValueError, RuntimeError, SyntaxError) as error:
        code = str(error) if isinstance(error, ValueError) and str(error).isupper() else 'INPUT_OR_ANALYSIS_FAILED'
        print(json.dumps(dict(status='ERROR', code=code)))
        return 2
    print(json.dumps(value, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
