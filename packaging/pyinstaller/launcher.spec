from pathlib import Path
import sys

from PyInstaller.utils.hooks import collect_submodules

project_root = Path(SPECPATH).parent.parent
sys.path.insert(0, str(project_root))
a = Analysis(
    [str(project_root / "shop_hoa_thuan" / "launcher.py")],
    pathex=[str(project_root)],
    hiddenimports=[*collect_submodules("apps.core"), *collect_submodules("shop_hoa_thuan")],
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
    name="ShopHoaThuanLauncher",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
)
