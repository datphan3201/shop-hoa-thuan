# PyInstaller spec — chạy trên Windows, không cross-compile từ WSL.
from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

project_root = Path(SPECPATH).parent.parent
# ``collect_submodules`` resolves packages before Analysis applies ``pathex``.
# Prefer this checkout's ``apps`` package over an unrelated installed package.
sys.path.insert(0, str(project_root))

datas = [
    # Version remains authored only in pyproject.toml; frozen code reads this
    # bundled copy instead of introducing a second version string.
    (str(project_root / "pyproject.toml"), "."),
    (str(project_root / "templates"), "templates"),
    (str(project_root / "staticfiles"), "staticfiles"),
]
datas += collect_data_files("django", include_py_files=False)

# ``dictConfig`` resolves this filter from a dotted string.  Keep it explicit:
# PyInstaller's module collector does not always retain modules that are only
# referenced through Django's logging configuration.
hiddenimports = [
    "apps.core.logging",
    *collect_submodules("apps.catalog"),
    *collect_submodules("apps.core"),
    *collect_submodules("apps.reports"),
    *collect_submodules("apps.sales"),
    *collect_submodules("django_htmx"),
    *collect_submodules("shop_hoa_thuan"),
    *collect_submodules("whitenoise"),
]

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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name="ShopHoaThuan",
)
