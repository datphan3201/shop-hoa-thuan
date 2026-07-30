$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:UV_PROJECT_ENVIRONMENT = ".venv-windows"

uv sync --group windows-build --python 3.12
uv run python manage.py collectstatic --noinput
uv run python manage.py check --deploy
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/shop_hoa_thuan.spec"

Write-Host "PyInstaller onedir đã tạo tại dist/ShopHoaThuan."
Write-Host "Bước tiếp theo: đặt WinSW-x64.exe đã kiểm tra checksum vào packaging/vendor/"
Write-Host "và biên dịch packaging/installer/ShopHoaThuan.iss bằng Inno Setup."
