# Separately obtained dependencies

NumPy, Pillow, Matplotlib and their transitive packages are obtained from PyPI using
requirements.lock, not redistributed as binaries in this source ZIP. DEPENDENCIES.json
records exact versions, metadata links and upstream license identifiers. Preserve
their upstream notices if distributing your own runtime. The standalone CPython
SDK is separately obtained using PYTHON-LOCK.json; its license applies separately.
The known-advisory lookup is an observation, not a security certification or future
advisory guarantee. Original microscopy images and tool XML are not dependencies.
