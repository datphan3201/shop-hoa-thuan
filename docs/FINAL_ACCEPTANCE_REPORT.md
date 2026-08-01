# Final acceptance report

## Kết luận hiện tại

**CONDITIONALLY ACCEPTED** — bản build và integration nội bộ đã có bằng chứng, nhưng chưa
được tuyên bố `ACCEPTED FOR PRODUCTION RELEASE`. Các gate cần UAC, reboot, clean Windows và
thiết bị thật vẫn chưa có bằng chứng trong môi trường hiện tại.

## Evidence đã có

- WSL full pytest sau thay đổi cuối: **122 passed, 1 warning**; warning là
  `override_settings(DATABASES=...)` trong restore test.
- Ruff, mypy, Django system check và migration consistency check đạt.
- Windows Python 3.12.10, PyInstaller 6.21.0 và Inno Setup 6.7.3.
- Native server `/health/` đạt trên test data.
- Native migration runner đạt, in được tiếng Việt và giải phóng maintenance lock.
- Health executable trả mã `SHOP-HEALTH-001` khi server chưa sẵn sàng.
- Installer `ShopHoaThuan-Setup-1.0.0.exe` build thành công.
- Backup/restore, update validation, tree replacement và exception-path được test trong WSL.

## Findings đã sửa

1. Standalone PyInstaller specs thiếu Python runtime binaries; đã nhúng `a.binaries`,
   `a.zipfiles` và `a.datas`.
2. Migration runner lỗi encoding cp1258 trên Windows; đã cấu hình UTF-8 có fallback.
3. Updater staging bị collision và có thể để file cũ; đã dùng staging riêng và thay toàn bộ
   application tree.
4. Restore tạo pre-restore backup trước khi validate package; đã đảo thứ tự để package sai
   không chạm dữ liệu vận hành.
5. Installer có warning `UninstallRun` thiếu `RunOnceId`; đã bổ sung định danh.

## Còn lại trước production

UAC service/firewall/recovery, clean Windows, reboot, LAN phone, camera/PWA thật, restore độc
lập và update/rollback native phải có PASS. Cho tới khi đó release decision không được nâng
cấp khỏi `CONDITIONALLY ACCEPTED`.
