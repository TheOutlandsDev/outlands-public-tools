"""Generate invented bar patterns; contains no original image pixels."""
import argparse
import json
from pathlib import Path


def image(shift=4.0, portrait=False):
    import numpy as np
    from PIL import Image
    axis = np.arange(640, dtype=float)
    def profile(offset):
        s = np.full(axis.shape, 180.0)
        for center in np.arange(100, 501, 40) + offset:
            s += 50 * np.exp(-0.5 * ((axis-center)/4)**2)
            for side in (-9, 9):
                s -= 160 * np.exp(-0.5 * ((axis-center-side)/2.2)**2)
        return np.clip(np.rint(s), 0, 255).astype('uint8')
    a = np.full((100, 640), 180, dtype='uint8')
    if portrait:
        # Portrait legacy windows differ from landscape; place strips at their
        # own declared locations rather than transposing the landscape fixture.
        a[2:34] = profile(0); a[47:79] = profile(shift)
        a = a.T.copy()
    else:
        a[14:45] = profile(0); a[54:85] = profile(shift)
    return Image.fromarray(a)


def generate(out):
    from vernier import ordinary
    from PIL import Image
    out = ordinary(out, False)
    out.mkdir()
    cases = []
    for name, shift, portrait in [('zero', 0, False), ('positive', 4, False), ('negative', -4, False), ('portrait', 4, True)]:
        image(shift, portrait).save(out / (name+'.png'))
        cases.append(dict(file=name+'.png',expected_verniers=shift/40,expected_um=shift/4,absolute_tolerance_verniers=0.002))
    Image.new('L', (640,100), 180).save(out/'blank.png')
    (out/'EXPECTED.json').write_text(json.dumps(dict(fictional=True,calibration_claimed=False,cases=cases,blank_expected='INSUFFICIENT_PATTERN'),indent=2)+'\n',encoding='utf-8')
    return dict(status='GENERATED',fictional=True,images=5)


if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True,type=Path)
    print(json.dumps(generate(p.parse_args().out)))
