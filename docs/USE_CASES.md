# Use case nghiệp vụ

## Vai trò

Phiên bản hiện tại có vai trò vận hành chính là **chủ shop/người dùng đã đăng nhập**. Django
admin chỉ bật khi development `DEBUG=True`, không phải workflow production. Giá vốn có lớp ủy
quyền tạm thời qua PIN, không phải role riêng.

## UC-01 — Thiết lập lần đầu

1. Mở `/setup/` trên database chưa có owner.
2. Nhập username, mật khẩu và PIN giá vốn.
3. Server tạo superuser và chỉ lưu PIN hash trong transaction.
4. Route tự đóng sau thành công; first-run lần nữa bị từ chối, không ghi đè dữ liệu.

Production chỉ installer/first-run runner gọi workflow này; service không tự chạy.

## UC-02 — Catalog và ảnh

- Tạo/sửa category, product và nhiều variant/size; nhập SKU, giá bán và tồn.
- Sửa cost cần cost lock mở.
- Upload JPEG/PNG/WebP từ camera/thư viện: server decode thật, giới hạn file/pixel, xử lý EXIF,
  nén và tạo thumbnail.
- Ngừng hoạt động dữ liệu thay vì hard-delete lịch sử.
- Nếu thiết bị khác đã sửa record, revision conflict báo tiếng Việt thay vì ghi đè.

## UC-03 — Điều chỉnh tồn kho

1. Chọn variant, nhập/thêm/trừ/đặt lại số lượng và lý do bắt buộc.
2. Server kiểm tra, cập nhật balance trong transaction.
3. Tạo `InventoryMovement` before/change/after và reference.
4. Retry cùng idempotency key không tạo movement thứ hai.

Không sửa quantity trực tiếp ngoài inventory service.

## UC-04 — Bán hàng/POS

1. Tìm product/SKU, chọn size còn hàng, số lượng và giá thực tế/discount.
2. Client gửi idempotency key và disable submit trong khi chờ.
3. Server transaction kiểm tra tồn tại commit, tính lại total, tạo sale/item snapshot/movement.
4. Nếu response mất sau commit, retry đúng key trả về sale cũ, không tạo sale mới.
5. Nếu thiếu tồn/lỗi, toàn bộ transaction rollback và không báo thành công.

UI disable size hết hàng, nhưng server vẫn là authority kiểm tra tồn.

## UC-05 — Hủy sale

1. Mở sale hoàn thành, nhập lý do hủy.
2. Server kiểm tra trạng thái trong transaction.
3. Cập nhật sale cancelled, lưu lý do/thời điểm, hoàn tồn và tạo `sale_return`.
4. Hủy lặp/retry không hoàn tồn lần hai.

## UC-06 — Báo cáo và giá vốn

- Dashboard/report chỉ dùng sale completed, ngày theo giờ Việt Nam.
- Cost lock đóng: response/context/CSV/hóa đơn không có giá vốn, lợi nhuận hoặc số liệu suy ra.
- Mở khóa cần PIN, rate-limit, tự hết hạn và khóa khi logout/khóa thủ công.
- Export cost cần unlock và xác nhận; export thường không chứa cost.

## UC-07 — Mobile/PWA

- Mobile có drawer/bottom navigation, card/list catalog/tồn/sale history và form chạm-friendly.
- Manifest có shortcut Bán hàng/Sản phẩm/Tồn kho. Worker chỉ cache static public GET.
- Không cache authenticated HTML, media, cost/profit, API nghiệp vụ hoặc POST; không offline write.
- Camera, Add to Home Screen, viewport/touch thật vẫn cần Phase 13 device validation.

## UC-08 — Backup, restore, update (mục tiêu chưa hoàn thành)

Thiết kế đã chốt nhưng GUI production chưa tồn tại:

- Backup: maintenance → block write mới → drain write cũ → SQLite backup API → integrity/
  checksum → DB + media + manifest.
- Restore: validate manifest/checksum/schema → backup current data → maintenance/staging →
  integrity/health/smoke → rollback DB/media nếu lỗi.
- Update: validate package/version → pre-update backup → stop/stage/swap app → migration →
  health/smoke → rollback khi lỗi.

Xem [roadmap](DELIVERY_ROADMAP.md) để biết thứ tự và gate thực hiện.
