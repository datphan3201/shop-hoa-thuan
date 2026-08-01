from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).parent.parent
sys.path.insert(0, str(project_root))
datas = [
    (str(project_root / "pyproject.toml"), "."),
    (str(project_root / "templates"), "templates"),
]
datas += collect_data_files("django", include_py_files=False)
a = Analysis(
    [str(project_root / "shop_hoa_thuan" / "restore_gui.py")],
    pathex=[str(project_root)],
    datas=datas,
    hiddenimports=[
        "apps.core.logging",
        *collect_submodules("apps.catalog"),
        *collect_submodules("apps.core"),
        *collect_submodules("apps.reports"),
        *collect_submodules("apps.sales"),
        *collect_submodules("django_htmx"),
        *collect_submodules("shop_hoa_thuan"),
        *collect_submodules("whitenoise"),
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="ShopHoaThuanRestore",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
