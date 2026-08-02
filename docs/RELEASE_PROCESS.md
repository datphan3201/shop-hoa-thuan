# Quy trình phát hành

## Nguồn và artifact

- Version duy nhất: `pyproject.toml`.
- Lock dependency: `uv.lock`.
- Build Windows: Python Windows project-local + PyInstaller `onedir` + Inno Setup.
- WinSW được xác minh checksum trước khi đưa vào staging; binary vendor không được lấy từ WSL.
- Runtime data luôn ở `%ProgramData%\\Shop Hoa Thuan`, ngoài `Program Files`.

## Evidence artifact hiện tại

- Baseline evidence version: `1.0.0`.
- Baseline installer: `ShopHoaThuan-Setup-1.0.0.exe`.
- Baseline installer SHA-256: `45B6EF4CF272E020ECC220F1C207737B19B401F83579886515C6B57657C096C6`.
- Current source release candidate: `1.2.0`, đọc từ `pyproject.toml`; artifact mới chưa có hash.
- Toolchain build: Windows Python 3.12.10, PyInstaller 6.21.0, Inno Setup 6.7.3,
  WinSW 2.12.0.0; WinSW SHA-256 đã xác minh trước khi đưa vào staging.
- Native server/migration/health smoke và service SCM/firewall/recovery test data đã đạt. Clean
  install, production ACL, reboot và thiết bị thật chưa được ghi PASS khi chưa có evidence tương ứng.

## Checklist release

1. WSL chạy formatter, Ruff, mypy, Django checks, migration check và full pytest.
2. Đồng bộ commit sạch sang Windows working copy.
3. Chạy `scripts/build_windows.ps1` bằng production-like env tạm.
4. Smoke-test server, migration, health và các GUI executable trong staging.
5. Build installer; lưu SHA-256 và version artifact.
6. Trên Windows nâng quyền: test service, LAN-scoped firewall trên Private/Public, crash recovery và cleanup.
7. Trên test data: backup → validate → restore; update 1.1.0 → 1.2.0 → rollback.
8. Lưu evidence không chứa dữ liệu thật; cập nhật `PROGRESS.md` và acceptance report.

Release update đang chuẩn bị:

- Version đích: `1.2.0`, đọc từ `pyproject.toml`.
- Update package: `ShopHoaThuan-Update-1.2.0.zip`, `current_version=1.1.0`,
  `target_version=1.2.0`.
- Nếu máy test đang ở `1.0.0`, tạo lại cùng package với `current_version=1.0.0`; updater yêu cầu
  manifest khớp chính xác version health hiện tại.
- Package phải được tạo từ cây frozen mới sau khi build Windows; native update, health, LAN và
  rollback vẫn phải có evidence trước khi đánh dấu PASS.

## Phân loại deployment warning

HTTP LAN có chủ đích giữ `security.W004`, `W008`, `W012`, `W016` khi
`SHOP_USE_HTTPS=false`. Đây là cảnh báo phải được chấp nhận bằng tài liệu, chỉ dùng mạng
LAN tin cậy với firewall `LocalSubnet` trên Private/Public. `W009`, wildcard `ALLOWED_HOSTS`, DEBUG production, secret ngắn và warning
không giải thích được phải sửa trước khi phát hành.
