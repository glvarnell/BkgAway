# Third-party notices

**rm_bkg** depends on open-source projects. This file summarizes attribution for
redistributors. Upstream license texts remain authoritative; when shipping
PyInstaller builds, include this file with the bundle and retain any license
files already collected under `_internal/`.

## Core background-removal stack

### transparent-background

- Project: https://github.com/plemeri/transparent-background  
- License: MIT  
- Used for: `Remover()` inference API and model download/cache layout  

### InSPyReNet

- Project: https://github.com/plemeri/InSPyReNet  
- License: MIT  
- Copyright (c) Taehun Kim and contributors  
- Used for: the saliency / background-removal model underlying `transparent-background`  

Model checkpoints downloaded at runtime are subject to the terms published by
those projects; keep their notices when redistributing pre-populated weight caches.

## UI

### PySide6 / Qt

- Project: https://doc.qt.io/qtforpython/ · https://www.qt.io/  
- License: LGPL v3 (PySide6 / Qt bindings as distributed on PyPI)  
- Used for: desktop UI  

If you distribute a frozen binary that includes Qt/PySide6, you must comply with
the LGPL (including providing copyright notices and meeting redistribution
obligations for LGPL libraries). See Qt and PySide6 license documentation.

## Machine learning / imaging (direct and transitive)

Exact versions depend on your install (`requirements-cuda.txt`,
`requirements-cpu.txt`, or `requirements-rocm.txt`) and the frozen build venv.

### PyTorch / torchvision

- Project: https://pytorch.org/ · https://github.com/pytorch/pytorch  
- License: BSD-style (see PyTorch `LICENSE`)  
- Used for: tensor compute / GPU or CPU inference  

### Pillow (PIL)

- Project: https://python-pillow.org/  
- License: HPND-derived Pillow license (see project `LICENSE`)  
- Used for: image load/save and preview conversion  

### NumPy

- Project: https://numpy.org/  
- License: BSD-3-Clause  
- Used for: array support via the imaging / ML stack  

### Other packages pulled in by transparent-background / vision stack

Frozen builds may also bundle libraries such as OpenCV (`cv2`), `timm`,
`albumentations`, `kornia`, `pymatting`, `scikit-image`, `tqdm`, `PyYAML`,
`gdown`, and related dependencies. Each retains its own license (commonly
MIT, Apache-2.0, or BSD). Consult the metadata and `LICENSE` files inside the
installed wheels or the `_internal` tree of a PyInstaller build.

## ComfyUI

This application aims to match the behavior of the ComfyUI **Inspyrenet Rembg**
node for convenience. It does **not** ship ComfyUI source. No ComfyUI license
notice is required for that behavioral compatibility alone.

## This project

See the repository `LICENSE` (when present) for terms covering `rm_bkg` itself.
