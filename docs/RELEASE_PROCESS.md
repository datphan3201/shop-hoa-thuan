# Quy trình phát hành

## Nguồn và artifact

- Version duy nhất: `pyproject.toml`.
- Lock dependency: `uv.lock`.
- Build Windows: Python Windows project-local + PyInstaller `onedir` + Inno Setup.
- WinSW được xác minh checksum trước khi đưa vào staging; binary vendor không được lấy từ WSL.
- Runtime data luôn ở `%ProgramData%\\Shop Hoa Thuan`, ngoài `Program Files`.

## Checklist release

1. WSL chạy formatter, Ruff, mypy, Django checks, migration check và full pytest.
2. Đồng bộ commit sạch sang Windows working copy.
3. Chạy `scripts/build_windows.ps1` bằng production-like env tạm.
4. Smoke-test server, migration, health và các GUI executable trong staging.
5. Build installer; lưu SHA-256 và version artifact.
6. Trên Windows nâng quyền: test service, Private firewall, crash recovery và cleanup.
7. Trên test data: backup → validate → restore; update 1.0.0 → 1.1.0 → rollback.
8. Lưu evidence không chứa dữ liệu thật; cập nhật `PROGRESS.md` và acceptance report.

## Phân loại deployment warning

HTTP LAN có chủ đích giữ `security.W004`, `W008`, `W012`, `W016` khi
`SHOP_USE_HTTPS=false`. Đây là cảnh báo phải được chấp nhận bằng tài liệu, chỉ dùng mạng
Private tin cậy. `W009`, wildcard `ALLOWED_HOSTS`, DEBUG production, secret ngắn và warning
không giải thích được phải sửa trước khi phát hành.
