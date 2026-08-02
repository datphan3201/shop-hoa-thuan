# Final acceptance report

## Kết luận hiện tại

**CONDITIONALLY ACCEPTED** — bản build và integration nội bộ đã có bằng chứng, nhưng chưa
được tuyên bố `ACCEPTED FOR PRODUCTION RELEASE`. Clean Windows, production ACL, reboot và
thiết bị thật vẫn chưa có bằng chứng trong môi trường hiện tại.

## Evidence đã có

- WSL full pytest sau thay đổi cuối: **137 passed, 1 warning**; warning là
  `override_settings(DATABASES=...)` trong restore test.
- Ruff, mypy, Django system check và migration consistency check đạt.
- Windows Python 3.12.10, PyInstaller 6.21.0 và Inno Setup 6.7.3.
- Native server `/health/` đạt trên test data.
- Native migration runner đạt, in được tiếng Việt và giải phóng maintenance lock.
- WinSW/SCM test data đạt: install/start, health, kill-process recovery, stop/start lại và
  firewall LAN-scoped trên Private/Public; service/rule được cleanup thành công.
- Health executable trả mã `SHOP-HEALTH-001` khi server chưa sẵn sàng.
- Installer `ShopHoaThuan-Setup-1.0.0.exe` build thành công.
- Native installer smoke sau khi rebuild: service `ShopHoaThuanServer` chạy, `/health/` trả HTTP
  200 với `status=ok`, `database=true`, `schema=true`, `version=1.0.0`, và database tồn tại
  đúng trong `C:\ProgramData\Shop Hoa Thuan\data\db.sqlite3`.
- Backup/restore, update validation, tree replacement và exception-path được test trong WSL.
- Native Windows test groups: operations 6 pass, runner/runtime 6 pass, update/service assets
  18 pass; full suite qua cầu WSL–Windows bị `KeyboardInterrupt` ở process console và vì vậy
  không được ghi là full Windows PASS.
- Hash SHA-256 của artifact rebuild cần được bổ sung từ output Windows; hash
  `45B6EF4CF272E020ECC220F1C207737B19B401F83579886515C6B57657C096C6` là bản build trước lỗi
  hostname và không còn là release evidence.

## Findings đã sửa

1. Standalone PyInstaller specs thiếu Python runtime binaries; đã nhúng `a.binaries`,
   `a.zipfiles` và `a.datas`.
2. Migration runner lỗi encoding cp1258 trên Windows; đã cấu hình UTF-8 có fallback.
3. Updater staging bị collision và có thể để file cũ; đã dùng staging riêng và thay toàn bộ
   application tree.
4. Restore tạo pre-restore backup trước khi validate package; đã đảo thứ tự để package sai
   không chạm dữ liệu vận hành.
5. Installer có warning `UninstallRun` thiếu `RunOnceId`; đã bổ sung định danh.
6. Clean-install 1.0.0 phát hiện hostname Windows tự động có dấu gạch dưới làm server từ chối
   `DJANGO_ALLOWED_HOSTS` và thoát trước khi bind cổng; đã lọc hostname tự phát hiện không hợp lệ,
   giữ validation nghiêm ngặt cho cấu hình explicit và thêm regression test. Artifact Windows phải
   được rebuild trước khi lặp lại clean-install.
7. Native inspection cho thấy installer chưa tạo production firewall rule. Đã bổ sung helper
   idempotent tạo rule theo `ShopHoaThuanServer.exe`, profile `Private/Public` với `LocalSubnet`,
   và cleanup khi uninstall; cần rebuild và kiểm thử LAN để đóng finding.

## Còn lại trước production

Clean Windows, reboot, LAN phone, camera/PWA thật, restore độc lập và update/rollback native
phải có PASS. Full Windows suite cũng cần được chạy trong một console native ổn định hoặc
Windows CI không bị cầu WSL ngắt. Cho tới khi đó release decision không được nâng cấp khỏi
`CONDITIONALLY ACCEPTED`.
