from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).parent.parent
sys.path.insert(0, str(project_root))
datas = [(str(project_root / "pyproject.toml"), "."), (str(project_root / "templates"), "templates")]
datas += collect_data_files("django", include_py_files=False)
hiddenimports = [
    "apps.core.logging",
    *collect_submodules("apps"),
    *collect_submodules("django_htmx"),
    *collect_submodules("shop_hoa_thuan"),
    *collect_submodules("whitenoise"),
]
a = Analysis(
    [str(project_root / "shop_hoa_thuan" / "migration_runner.py")],
    pathex=[str(project_root)],
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
    name="ShopHoaThuanMigration",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)
COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name="ShopHoaThuanMigration")
