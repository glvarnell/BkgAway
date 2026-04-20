# -*- mode: python ; coding: utf-8 -*-
# Build a distributable folder for NVIDIA CUDA PyTorch.
# Prerequisite: active venv with `pip install -r requirements-cuda.txt pyinstaller`
# Run from repository root: pyinstaller packaging/rm_bkg_cuda.spec

from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis
from PyInstaller.utils.hooks import collect_all, collect_dynamic_libs

spec_path = Path(SPEC)
repo_root = spec_path.parent.parent
entry = repo_root / "packaging" / "entrypoint_gui.py"

datas: list = []
binaries: list = []
hiddenimports: list = [
    "rm_bkg",
    "rm_bkg.__main__",
    "rm_bkg.main_window",
    "rm_bkg.remover_worker",
    "rm_bkg.drop_widgets",
    "rm_bkg.images",
]

packages = [
    "torch",
    "torchvision",
    "transparent_background",
    "cv2",
    "albumentations",
    "albucore",
    "timm",
    "kornia",
    "pymatting",
    "numpy",
    "PIL",
    "yaml",
    "tqdm",
    "gdown",
    "wget",
    "easydict",
    "skimage",
]

for pkg in packages:
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception:
        pass

for lib in ("torch", "nvidia", "triton"):
    try:
        binaries += collect_dynamic_libs(lib)
    except Exception:
        pass

excludes = [
    "tkinter",
    "IPython",
    "jupyter",
    "notebook",
    "pytest",
]

a = Analysis(
    [str(entry)],
    pathex=[str(repo_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="rm-bkg-cuda",
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=True,
    upx=False,
    upx_exclude=[],
    name="rm-bkg-cuda",
)
