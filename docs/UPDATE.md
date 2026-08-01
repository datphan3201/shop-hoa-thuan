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

## Giới hạn đã biết

Updater native yêu cầu kiểm thử trong Windows Service Control Manager; test WSL chỉ chứng minh
validation/staging/maintenance và tree replacement. Reboot, mất điện và failure injection
trên máy cài thật được ghi là `BLOCKED` cho đến khi có phiên Windows nâng quyền.
