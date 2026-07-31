# Kiến trúc Shop Hoà Thuận

## Phạm vi

Shop Hoà Thuận là ứng dụng nội bộ cho shop quần áo: danh mục, sản phẩm theo size, tồn kho,
bán hàng, hủy giao dịch, báo cáo và bảo vệ giá vốn. Mục tiêu phát hành là phần mềm cài trên
Windows, dùng từ thiết bị trong LAN mà không yêu cầu cloud hay terminal trên máy người dùng.

Phase 1–8 đã hoàn thành; Phase 9 đang triển khai. Chưa được dùng dữ liệu thật cho đến khi các
gate Windows, backup/restore, update/rollback và thiết bị thật của Phase 9–13 có evidence.

## Sơ đồ thành phần

```text
Browser desktop / điện thoại
        │ HTTP LAN tin cậy hoặc HTTPS/Tailscale cấu hình đúng
        ▼
Waitress (một process) ── Django Templates + HTMX + static local
        │
        ├── catalog / inventory / sales / reports services
        ├── idempotency + optimistic concurrency
        ├── cost-price security, authentication, private media
        ├── server lease, maintenance và active-write coordination
        └── health + structured production logging
        │
        ▼
SQLite + media + backup + log + config trong runtime data directory
```

Trong bản Windows, WinSW chạy `ShopHoaThuanServer.exe`. Launcher chỉ kiểm tra `/health/`, yêu
cầu Service Control Manager start service khi cần, rồi mở browser; nó không spawn server khác.

## Các lớp ứng dụng

| Lớp | Trách nhiệm | Quy tắc |
|---|---|---|
| `apps.core` | Auth, PIN, runtime, lock, health, private media, idempotency | Không trả cost khi khóa; không log secret/token/PIN. |
| `apps.catalog` | Category, Product, Variant, InventoryMovement | Chỉ inventory service thay đổi `ProductVariant.quantity`. |
| `apps.sales` | Giỏ, Sale, SaleItem, hủy sale | Bán/hủy trong `transaction.atomic()`; lưu snapshot. |
| `apps.reports` | Dashboard, report, export | Chỉ tính sale hoàn thành; ngày theo `Asia/Ho_Chi_Minh`. |
| `shop_hoa_thuan` | Settings, runtime, server, runner, version | Server không tự migrate hoặc first-run. |

Views giữ mỏng; forms validation; services thực hiện quy tắc/transaction; database giữ
constraint quan trọng. Tiền lưu bằng số nguyên VND, không dùng float.

## Runtime data

```text
C:\Program Files\Shop Hoa Thuan\        application thay thế được khi update
C:\ProgramData\Shop Hoa Thuan\          dữ liệu phải được giữ lại
├── data\db.sqlite3
├── data\media\
├── backups\
├── rollback\
├── logs\
└── config\django-secret-key
```

WSL development mặc định dùng `<repository>/.data`; `SHOP_DATA_DIR` đổi được vị trí runtime.
Không dùng live database trên OneDrive/cloud sync, USB, NAS hay network share.

## Consistency và concurrency

- Nhập, trừ, đặt lại tồn và hoàn tồn đều tạo `InventoryMovement`.
- Sale tạo `Sale`, `SaleItem`, trừ tồn và movement trong một transaction; lỗi ở bất cứ dòng nào
  rollback toàn bộ.
- Hủy sale chỉ hợp lệ một lần, có lý do và tạo `sale_return`.
- Server tính lại subtotal, discount và total; không tin tổng từ client.
- Idempotency ràng buộc `(user, operation, key)` cùng fingerprint: retry cùng payload trả kết
  quả cũ, reuse key với payload khác bị từ chối.
- Record quan trọng dùng `revision`; stale form bị từ chối thay vì ghi đè. Sale/tồn vẫn dùng
  transaction server authoritative.

## Một instance và maintenance

`FileLease` dùng advisory lock OS trên guard file cạnh metadata JSON, scope theo runtime data
directory. Lock OS là authority, metadata PID chỉ phục vụ chẩn đoán; điều này giảm stale
PID/PID reuse/TOCTOU. Hai Waitress/service cùng data directory không thể cùng sở hữu server
lease.

Maintenance lấy lease, chặn write mới, chờ active-write marker hiện hữu drain trong timeout,
rồi chạy backup/migration/restore/update. Mọi path release lease/state bằng `finally`. Timeout
không kill transaction đang ghi; maintenance kết thúc an toàn. Service runtime không migration
hay first-run.

## Bảo mật, media, health và log

- Django auth, CSRF, HTTP-only cookie; `SHOP_USE_HTTPS=true` chỉ khi HTTPS thực có.
- `DJANGO_ALLOWED_HOSTS` không chấp nhận wildcard; dùng localhost, hostname/IP LAN phát hiện
  hoặc host cấu hình rõ.
- Cost/PIN hash không ra response/context/export/log khi cost lock đóng.
- Product media cần login, bị giới hạn trong media root và chỉ JPEG/PNG/WebP decode hợp lệ.
- Log server, security, business, backup, restore, update, service xoay tối đa 5 file/category;
  filter che password, PIN, session, CSRF, authorization, secret và cost price.
- `/health/` nhẹ, không trả stack trace/path/secret/dữ liệu nghiệp vụ; phản ánh version,
  database, maintenance và schema compatibility.

Version authored duy nhất là `pyproject.toml`, được bundle vào executable để UI, health, backup
manifest và artifact dùng cùng giá trị.

## Trạng thái Windows

PyInstaller `onedir` native `ShopHoaThuanServer.exe` đã smoke PASS `/health/` trên Windows test
data. Gate WinSW/SCM/firewall/recovery vẫn cần chạy với Administrator. Installer, restore GUI và
updater chưa hoàn thành; xem [roadmap](DELIVERY_ROADMAP.md).
