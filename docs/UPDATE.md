# Cập nhật và rollback

## Phạm vi

Updater bản đầu nhận một ZIP cục bộ, không tải code từ Internet và không cần người dùng chạy
terminal. Gói phải chứa `update-manifest.json` và một cây `application/` hoàn chỉnh. Mỗi file
trong manifest có SHA-256; version đích phải lớn hơn version hiện tại theo Semantic Versioning.

## Luồng cập nhật

1. Kiểm tra version hiện tại, version đích, checksum, đường dẫn ZIP và schema.
2. Lấy maintenance lease; request ghi mới bị từ chối và active write được drain với timeout.
3. Tạo và xác minh pre-update backup.
4. Dừng Windows Service; sao lưu cây application cũ vào `rollback/`.
5. Stage gói vào thư mục tạm; thay toàn bộ application tree để không còn file cũ sót lại.
6. Chạy `ShopHoaThuanMigration.exe`; server runtime không tự chạy migration.
7. Start service, kiểm tra `/health/` và smoke test; chỉ khi đạt mới kết thúc operation.
8. Dọn staging trong `finally`.

Bản update từ `1.0.0` lên `1.1.0` cũng cập nhật trang device access: SSID, adapter và địa chỉ
IPv4 Wi-Fi được đọc lại khi mở/làm mới trang; mã QR được tạo lại từ URL hiện tại. Update runner
chạy từ bản sao tạm ngoài `Program Files`, sau đó áp dụng firewall rule Private từ cây application
mới trước khi khởi động service.

Updater 1.1.0 có thể bootstrap bản cài 1.0.0: nó đọc version đang chạy từ `/health/`, tự dùng
`C:\Program Files\Shop Hoa Thuan` làm app root mặc định khi chạy từ thư mục tạm, và truyền rõ
`current_version` vào transaction. Vì vậy không cần chạy updater cũ đang nằm trong application tree.

Trên máy test không có `C:\Projects`, chỉ cần chép `ShopHoaThuanUpdate.exe` mới và ZIP update vào
một thư mục tạm, ví dụ `C:\Temp\ShopHoaThuanUpdate`. Chạy updater mới bằng **Run as administrator**,
chọn `ShopHoaThuan-Update-1.1.0.zip`, rồi kiểm tra `/health/` trả `version=1.1.0`. Không gỡ cài đặt
trước khi update; ProgramData, database và media phải được giữ nguyên.

Nếu migration, service hoặc health thất bại, updater dừng bản mới, phục hồi application tree
cũ và restore pre-update backup nếu cần, rồi khởi động bản cũ. Maintenance lease luôn được
giải phóng bởi context manager.

## Tạo gói

`source-root` phải là cây đầy đủ, bao gồm migration runner dưới
`ShopHoaThuanMigration/ShopHoaThuanMigration.exe`. Không đưa database, media, config, secret,
log hoặc backup vào gói.

```text
uv run python scripts/build_update_package.py --source-root <frozen-application-directory> --output <release-directory>/ShopHoaThuan-Update-1.1.0.zip --current-version 1.0.0 --target-version 1.1.0
```

`<frozen-application-directory>` phải chứa `configure_firewall.ps1`; build Windows tự copy file
này vào `dist\ShopHoaThuan`. Không đưa database, media, config, secret, log hoặc backup vào gói.

## Giới hạn đã biết

Updater native yêu cầu kiểm thử trong Windows Service Control Manager; test WSL chỉ chứng minh
validation/staging/maintenance và tree replacement. Reboot, mất điện và failure injection
trên máy cài thật được ghi là `BLOCKED` cho đến khi có phiên Windows nâng quyền.
