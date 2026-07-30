# Tiến độ Shop Hoà Thuận

Cập nhật gần nhất: 2026-07-31

## Trạng thái hiện tại

Phase 3 — Khóa giá vốn và thống kê tồn: **hoàn thành**

## Quyết định kiến trúc

- Django 5.2 LTS trên Python 3.12.
- Django monolith, server-rendered Templates; HTMX chỉ cho tương tác cục bộ.
- SQLite bật foreign keys, WAL và busy timeout để tăng độ bền trên một máy shop.
- Một tiến trình Waitress; các thao tác ghi quan trọng vẫn dùng transaction ngắn.
- Dữ liệu vận hành tách khỏi mã/bộ cài, mặc định:
  - Windows: `%PROGRAMDATA%\Shop Hoa Thuan`;
  - development: `<repository>/.data`;
  - có thể đổi bằng `SHOP_DATA_DIR`.
- Ảnh gốc được resize và tạo thumbnail; không lưu ảnh trong database.
- Bootstrap, HTMX và Chart.js được đóng gói local để ứng dụng hoạt động khi mất Internet.
- PyInstaller `onedir`, Windows Service và Inno Setup là pipeline phát hành; máy shop
  không cần Python, uv, Git hay Node.js.
- Truy cập LAN/Tailscale dùng HTTP ở bản đầu. Phiên đăng nhập, CSRF và giới hạn host vẫn
  được bật; hướng dẫn thiết bị cảnh báo chỉ dùng mạng tin cậy.

## Rủi ro kỹ thuật chính

| Rủi ro | Ảnh hưởng | Biện pháp |
|---|---|---|
| Mất điện khi SQLite đang ghi | Mất/không nhất quán giao dịch | WAL, transaction nguyên tử, foreign keys, backup định kỳ và kiểm tra integrity |
| Hai thao tác bán cùng lúc | Bán quá tồn | Transaction, cập nhật có điều kiện và khóa ghi SQLite ngắn |
| Bộ cài nâng cấp ghi đè dữ liệu | Mất database/media | Dữ liệu nằm ngoài thư mục cài; installer không xóa data dir |
| Máy đổi IP | Điện thoại khó truy cập | Hiển thị địa chỉ LAN/Tailscale trong trang thiết bị; ưu tiên hostname/Tailscale |
| Windows Service không có Desktop session | Không tự mở trình duyệt | Service chỉ chạy server; shortcut Desktop mở URL/PWA riêng |
| Secret/PIN bị lộ | Lộ dữ liệu nhạy cảm | Hash Django, session HTTP-only, không gửi giá vốn khi khóa, giới hạn thử PIN |
| Ảnh dung lượng lớn | Tốn đĩa/RAM | Kiểm tra định dạng/kích thước, resize và thumbnail bằng Pillow |
| Backup không dùng được | Mất khả năng phục hồi | Backup nhất quán gồm DB + media + manifest; kiểm tra ZIP và quy trình restore có xác nhận |
| Truy cập LAN qua HTTP | Cookie có thể bị nghe lén trên mạng xấu | Chỉ mạng tin cậy/Tailscale; tài liệu hóa HTTPS/Tailscale khi truy cập từ xa |
| PyInstaller không cross-compile từ WSL | Không tạo được `.exe` chỉ bằng Linux | Giữ development/test trong WSL; chạy pipeline build cuối trên Windows sạch hoặc Windows CI |

## Kế hoạch triển khai

### Phase 1 — Nền tảng

- [x] Kiểm tra repository và WSL toolchain.
- [x] Chốt Python 3.12, uv và project-local virtualenv.
- [x] Tạo `AGENTS.md`, `PROGRESS.md`, `.env.example`.
- [x] Khởi tạo Django, settings, logging, static/media/data dir.
- [x] Tạo schema cốt lõi, migration và database constraints.
- [x] Thiết lập đăng nhập/đăng xuất, bảo vệ route và tài khoản cài đặt lần đầu.
- [x] Tạo layout quản trị, sidebar/header/mobile navigation và route khung.
- [x] Tạo `/health/` không làm lộ dữ liệu.
- [x] Tạo backup nhất quán, kiểm tra archive và giao diện tải backup.
- [x] Tạo khung Waitress, PyInstaller onedir, WinSW và Inno Setup.
- [x] Format, lint, mypy, Django checks, migrations check và tests.
- [x] Commit Phase 1.

Điều kiện hoàn thành: ứng dụng khởi động bằng Waitress, đăng nhập được, route quản trị
được bảo vệ, schema/migration sạch, health check hoạt động, toàn bộ kiểm tra Phase 1 qua.

### Phase 2 — Sản phẩm và tồn kho

- [x] CRUD/soft-disable loại mặt hàng, sản phẩm và size.
- [x] Upload/resize ảnh và tạo thumbnail.
- [x] Tìm kiếm/lọc theo tên, SKU, loại, size, màu, tồn kho và trạng thái.
- [x] Hiển thị size còn hàng, sắp hết và hết hàng từ biến thể hiện tại.
- [x] Inventory service nguyên tử cho nhập, trừ và đặt số lượng.
- [x] Bắt buộc lý do và tạo lịch sử cho mọi biến động.
- [x] Unit/integration tests cho constraints, ảnh, sản phẩm và tồn kho.
- [x] Commit Phase 2.

### Phase 3 — Khóa giá vốn và thống kê tồn

- [x] Thiết lập/đổi PIN và chỉ lưu hash Django.
- [x] Giới hạn 5 lần thử sai và tạm khóa 5 phút.
- [x] Session HTTP-only mở khóa ngắn hạn, browser-session và khóa thủ công.
- [x] Tự khóa khi hết hạn, đăng xuất hoặc đổi thời gian.
- [x] Chặn tạo/sửa giá vốn và tải backup khi đang khóa.
- [x] Defer giá vốn khỏi queryset và không render số liệu nhạy cảm khi khóa.
- [x] Thống kê vốn tồn, giá trị bán, lợi nhuận và tỷ suất theo từng size.
- [x] Unit/integration tests cho PIN, expiry, logout, rate limit và response.
- [x] Commit Phase 3.

### Phase 4 — Bán hàng

- Màn hình bán hàng tối ưu bàn phím.
- Transaction bán hàng nguyên tử, snapshot và trừ kho.
- Lịch sử/chi tiết/in hóa đơn.
- Hủy đúng một lần và hoàn tồn.
- Test cạnh tranh và tính bất biến lịch sử.

### Phase 5 — Dashboard và báo cáo

- Dashboard, báo cáo theo múi giờ Việt Nam và Chart.js.
- Doanh thu, bán chạy, tồn thấp/hết.
- CSV mặc định không có giá vốn; export nhạy cảm cần mở khóa/xác nhận.

### Phase 6 — Hoàn thiện và phát hành Windows

- Hoàn thiện unit/integration/E2E smoke tests.
- Audit auth, CSRF, session, PIN, dữ liệu nhạy cảm và SQLite integrity.
- Backup/restore bằng giao diện và kiểm thử chuyển máy.
- PyInstaller onedir, Waitress, WinSW, shortcut Desktop/PWA và Inno Setup.
- Tài liệu cài đặt lần đầu, truy cập điện thoại, nâng cấp, backup/restore.
- Kiểm thử trên Windows sạch không cài Python/uv/Git/Node.

## Nhật ký kiểm tra

### Phase 1 — 2026-07-31

- Python: 3.12.13; Django: 5.2.16 LTS.
- `ruff format --check`: đạt.
- `ruff check`: đạt.
- `mypy --strict`: đạt, 45 source files.
- `manage.py check`: đạt, không có issue.
- `makemigrations --check --dry-run`: không có thay đổi model chưa migration.
- `pytest`: 21 test đạt.
- Waitress smoke test: khởi động production entry point, migrate/seed và `/health/` đạt.
- Static assets Bootstrap/HTMX/Chart.js được phục vụ local.
- `check --deploy` còn cảnh báo HTTPS/secure cookie có chủ đích vì bản local LAN chạy HTTP;
  rủi ro và hướng Tailscale/HTTPS đã được ghi nhận cho Phase 6.
- Restore từ giao diện và kiểm thử bộ cài Windows sạch vẫn thuộc Phase 6.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 1.

### Phase 2 — 2026-07-31

- `ruff format --check` và `ruff check`: đạt.
- `mypy --strict`: đạt, 50 source files.
- Django system/migration checks: đạt.
- `pytest`: 29 test đạt.
- Waitress smoke test: đạt sau migration mới.
- Ảnh test và database development tạm đã được dọn khỏi workspace.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 2.

### Phase 3 — 2026-07-31

- `ruff format --check`, `ruff check`, `mypy --strict`: đạt.
- Django system/migration checks: đạt.
- `pytest`: 38 test đạt.
- Waitress smoke test: đạt.
- Không sử dụng `localStorage`; phiên mở khóa chỉ nằm trong Django session.
- Backup chứa database chỉ tạo/tải được khi giá vốn đã mở khóa.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 3.
