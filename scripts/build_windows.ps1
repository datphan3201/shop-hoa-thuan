$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

$env:UV_PROJECT_ENVIRONMENT = ".venv-windows"

$python = Join-Path $ProjectRoot ".venv-windows\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
    throw "Thiếu Python Windows project-local: $python"
}
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "Thiếu uv Windows. Không tự cài trong script build."
}
$version = & $python -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($version)) {
    throw "Không đọc được version từ pyproject.toml."
}

uv sync --group windows-build --python 3.12
uv run python manage.py collectstatic --noinput
# Deployment checks must exercise production-like settings.  These values are
# process-local build fixtures; the installer generates the real runtime secret
# and configuration in ProgramData.
$env:DJANGO_DEBUG = "false"
$env:DJANGO_SECRET_KEY = "build-check-$([guid]::NewGuid().ToString('N'))-not-for-runtime"
$env:DJANGO_ALLOWED_HOSTS = "localhost,127.0.0.1"
uv run python manage.py check --deploy
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/shop_hoa_thuan.spec"
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/migration_runner.spec"
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/health_check.spec"
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/launcher.spec"
uv run pyinstaller --noconfirm --clean "packaging/pyinstaller/update_gui.spec"

$iscc = Get-Command iscc -ErrorAction SilentlyContinue
if ($null -eq $iscc) {
    $candidate = Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"
    if (Test-Path -LiteralPath $candidate -PathType Leaf) {
        $iscc = Get-Item -LiteralPath $candidate
    }
    else {
        throw "Thiếu Inno Setup Compiler (iscc). Cài tool chính thức trước khi tạo installer."
    }
}
if (-not (Test-Path -LiteralPath "packaging\vendor\WinSW-x64.exe" -PathType Leaf)) {
    throw "Thiếu packaging\vendor\WinSW-x64.exe đã xác minh checksum."
}
$isccPath = if ($iscc.PSObject.Properties.Name -contains "Source") { $iscc.Source } else { $iscc.FullName }
& $isccPath "/DAppVersion=$version" "packaging\installer\ShopHoaThuan.iss"
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup build thất bại."
}

Write-Host "Build Windows hoàn tất version ${version}: dist/ và dist/installer/."
