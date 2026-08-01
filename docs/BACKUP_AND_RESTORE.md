# Backup và restore

## Phạm vi

Backup là file ZIP nhất quán gồm:

- `db.sqlite3` — snapshot qua SQLite backup API, không copy trực tiếp database đang ghi.
- `media/` — ảnh gốc và thumbnail.
- `manifest.json` — application version, schema version, UTC timestamp, timezone,
  SHA-256 database, inventory media và số lượng record/tồn/doanh thu hoàn thành.

Backup/restore lấy maintenance operation. Request ghi mới bị chặn, active write được drain có
timeout; lỗi hoặc timeout luôn giải phóng maintenance. Backup chỉ báo thành công sau integrity
check, checksum và ZIP validation.

## Backup từ giao diện

Mở **Thiết bị và sao lưu**, mở khóa giá vốn bằng PIN rồi chọn **Tạo bản sao lưu**. Không cần
terminal. Nút có idempotency key để retry không tạo hai archive. File ZIP hoàn chỉnh có thể copy
ra USB hoặc lưu trữ khác; không đồng bộ live `db.sqlite3`.

Trên Windows có thêm `ShopHoaThuanBackup.exe` trong Start Menu. Utility này dùng cùng
maintenance/SQLite snapshot với giao diện web. `prune_backups()` giữ theo cửa sổ daily/weekly/
monthly và không xóa archive có file đánh dấu `.keep`.

## Restore từ giao diện

1. Chọn file ZIP backup.
2. Kiểm tra manifest, đường dẫn, checksum database/media và SQLite integrity.
3. Nhập chính xác `KHÔI PHỤC` để xác nhận mạnh.
4. Hệ thống tạo pre-restore backup hiện tại.
5. Maintenance thay database/media bằng staging đã kiểm tra.
6. Nếu thay đổi lỗi, rollback từ dữ liệu hiện tại trong `rollback/` và báo lỗi.

Sau restore cần kiểm tra dashboard, tồn kho, giao dịch gần nhất, ảnh sản phẩm và PIN. Restore
production thực tế phải được chạy trên bản sao hoặc môi trường test trước; không dùng dữ liệu
thật cho failure injection.

Trên Windows có `ShopHoaThuanRestore.exe`; utility yêu cầu chọn ZIP, xác nhận mạnh `KHÔI PHỤC`
và hiển thị pre-restore backup sau khi hoàn tất.

## Giữ lại và phục hồi

Installer/update không xóa `ProgramData`. Pre-restore backup được giữ trong backup root; bản
rollback tạm nằm trong `rollback/` để điều tra. Việc cleanup chỉ được thực hiện sau khi health,
integrity và record counts đã được xác minh.
