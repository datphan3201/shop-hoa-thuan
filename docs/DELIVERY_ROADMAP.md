# Roadmap phát hành và việc cần làm tiếp theo

## Trạng thái tại 2026-08-01

| Phase | Trạng thái | Evidence | Gate còn lại |
|---|---|---|---|
| 1–7 | Hoàn thành | Nghiệp vụ, runtime hardening, lock/maintenance, health/media/logging test | Chứng nhận Windows thuộc phase phát hành. |
| 8 | Hoàn thành trong WSL | Mobile/PWA, idempotency, concurrency, upload/media | Camera/viewport/A2HS thật ở Phase 13. |
| 9 | Đang triển khai, native smoke PASS | Waitress, launcher source, WinSW XML, device page, native server/migration/health smoke | WinSW/SCM/firewall/recovery cần UAC; reboot/LAN phone cần device validation. |
| 10 | Build artifact PASS, acceptance pending | PyInstaller server + standalone utilities + Inno Setup installer build PASS | Clean install/reinstall/uninstall trên Windows sạch chưa chạy. |
| 11 | Backend/GUI/WSL PASS, native acceptance pending | SQLite backup API, manifest/checksum/integrity, restore và GUI utility | Restore bằng installer/service thật và retention scheduler cần kiểm thử thêm. |
| 12 | WSL validation PASS, native acceptance pending | Package validation, staging cleanup, complete tree replacement, rollback primitives | 1.0.0→1.1.0 với SCM/migration/health failure injection chưa chạy. |
| 13 | Evidence lập xong ở mức internal, chưa accepted | Traceability, acceptance, limitations, checklist và user validation docs | UAC, reboot, clean Windows, LAN phone và camera thật. |

Không bắt đầu phase kế tiếp trước khi gate phase hiện tại đạt hoặc được ghi rõ `BLOCKED FOR
DEVICE VALIDATION`; không ghi PASS giả.

## Điều kiện truy cập xuyên phase

Ứng dụng dùng trực tiếp trong LAN, không có account hoặc mật khẩu nghiệp vụ. Browser session
chỉ phục vụ mở khóa PIN giá vốn và idempotency; nó không là cơ chế phân quyền. Vì vậy:

- Phase 9 phải xác minh firewall chỉ profile Private, không public Internet/port-forward và
  launcher không tạo server thứ hai.
- Phase 10 không được tạo hay reset account; installer chỉ tạo runtime secret và hướng dẫn PIN
  khi chưa được thiết lập.
- Phase 11–12 phải giữ nguyên PIN hash/config hiện có khi backup, restore, update hoặc rollback.
- Phase 13 phải đánh giá biên LAN, Wi-Fi khách, firewall và rò rỉ dữ liệu giá vốn; PIN không
  được xem là kiểm soát truy cập cho sale/inventory.

## Việc ngay: hoàn tất Phase 9

### Integration test service cần Administrator

Điều kiện: `C:\Projects\ShopHoaThuan` đã sync đúng Git commit, native server tồn tại, WinSW
portable đã tải/xác minh. Mở PowerShell bằng **Run as administrator** và chạy:

```powershell
& "C:\Projects\ShopHoaThuan\scripts\windows\phase9_test_service.ps1" `
  -AppRoot "C:\Projects\ShopHoaThuan\dist\ShopHoaThuan" `
  -WinSwPath "C:\Projects\ShopHoaThuan\packaging\vendor\WinSW-x64.exe" `
  -ProjectRoot "C:\Projects\ShopHoaThuan" `
  -PythonExe "C:\Projects\ShopHoaThuan\.venv-windows\Scripts\python.exe"
```

Script chỉ dùng data `C:\ProgramData\Shop Hoa Thuan Test`, service `ShopHoaThuanTestServer` và
rule `Shop Hoa Thuan Test LAN 2505`. Nó explicit migrate data test (không phải service startup),
install/start service, health, kill PID để test recovery, stop/start lại và tự gỡ service/rule.
Data/log test được giữ để điều tra.

**PASS:** health thành công trước/sau recovery; firewall chỉ Private; không còn test service/rule
sau cleanup. **FAIL:** giữ log/data test, không chạm `C:\ProgramData\Shop Hoa Thuan` production.

### Sau test SCM

1. Build launcher `.exe`; smoke khi service đã chạy và khi service dừng.
2. Kiểm tra URL/QR trên LAN thật, không Internet và sau đổi IP.
3. Chuẩn bị/check reboot auto-start và phone LAN; ghi `REQUIRES USER DEVICE VALIDATION` nếu chưa
   thể chạy, không đánh dấu PASS.
4. Full WSL gate + Windows baseline, review, cập nhật progress, commit Phase 9 sạch.

## Phase 10 — Installer

1. Tạo executable riêng cho server, launcher, migration và health.
2. Bundle templates/static/migrations/dynamic middleware/version metadata; smoke staging.
3. Inno Setup: Program Files app, ProgramData preserved, secret/config, migration,
   service/firewall/health/shortcut và hướng dẫn thiết lập PIN.
4. Test install/reinstall/uninstall giữ data và failure rollback.

## Phase 11 — Backup/restore

1. Backup package DB/media/manifest version-schema-timezone/checksum/counts; implementation và
   WSL restore test đã đạt.
2. Maintenance + SQLite backup API + integrity, GUI và retention 7 daily/4 weekly/12 monthly.
3. Restore validate → backup current → stage/swap → migration/integrity/health → rollback.
4. Test restore thật, media/count/tồn/sale/config và failure path.

## Phase 12 — Update/rollback

1. Tạo update 1.0.0 → 1.1.0 migration additive, validate package/version/checksum/disk/schema;
   validation/staging/tree replacement đã đạt trong WSL.
2. Maintenance/drain/pre-backup → stop service → stage/swap → migration/deploy check → health.
3. Tiêm lỗi migration/service/health/asset; rollback app/data/service/maintenance.

## Phase 13 — Acceptance

1. Traceability matrix, acceptance report, known limitations, release checklist và evidence.
2. Business/security/concurrency/performance suite gần dataset mục tiêu.
3. Clean Windows installer/reboot/reinstall/uninstall; backup→restore; update→rollback.
4. Mobile real-device: LAN, camera, PWA Add to Home Screen, touch UX.
5. Chỉ `ACCEPTED FOR PRODUCTION RELEASE` khi 0 Critical/High và toàn bộ gate có evidence.

## Quality gate mỗi phase

```bash
~/.local/bin/uv run ruff format --check .
~/.local/bin/uv run ruff check .
~/.local/bin/uv run mypy .
~/.local/bin/uv run python manage.py check
~/.local/bin/uv run python manage.py makemigrations --check --dry-run
~/.local/bin/uv run pytest
```

Sau thay đổi Windows, sync bằng Git (không copy `.venv`, data, log, secret), chạy baseline
Windows/native smoke và integration phù hợp; ghi tool version, command, result, warning và test
chưa thể chạy vào `PROGRESS.md`/evidence.
