"""Invented image generator adapted from the published vernier source."""
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
