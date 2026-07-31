# PyInstaller spec — chạy trên Windows, không cross-compile từ WSL.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).parent.parent

datas = [
    (str(project_root / "templates"), "templates"),
    (str(project_root / "staticfiles"), "staticfiles"),
]
datas += collect_data_files("django", include_py_files=False)

hiddenimports = collect_submodules("apps") + collect_submodules("shop_hoa_thuan")

a = Analysis(
    [str(project_root / "shop_hoa_thuan" / "server.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ShopHoaThuanServer",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    name="ShopHoaThuan",
)
