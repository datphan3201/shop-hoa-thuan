# Kiến trúc Shop Hoà Thuận

## Phạm vi

Shop Hoà Thuận là ứng dụng nội bộ cho shop quần áo: danh mục, sản phẩm theo size, tồn kho,
bán hàng, hủy giao dịch, báo cáo và bảo vệ giá vốn. Mục tiêu phát hành là phần mềm cài trên
Windows, dùng từ thiết bị trong LAN mà không yêu cầu cloud hay terminal trên máy người dùng.

Phase 1–8 đã hoàn thành trong WSL. Phase 9–12 có source, test nền tảng và Windows artifact;
Phase 13 có evidence nội bộ nhưng chưa đạt toàn bộ acceptance gate Windows/thiết bị thật.
Không dùng dữ liệu thật cho failure injection.

## Sơ đồ thành phần

```text
Browser desktop / điện thoại
        │ HTTP LAN tin cậy hoặc HTTPS/Tailscale cấu hình đúng
        ▼
Waitress (một process) ── Django Templates + HTMX + static local
        │
        ├── catalog / inventory / sales / reports services
        ├── idempotency + optimistic concurrency
        ├── cost-price PIN security, LAN media delivery
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
| `apps.core` | PIN, runtime, lock, health, media, idempotency | Không trả cost khi khóa; không log secret/token/PIN. |
| `apps.catalog` | Category, Product, Variant, InventoryMovement | Chỉ inventory service thay đổi `ProductVariant.quantity`. |
| `apps.sales` | Giỏ, Sale, SaleItem, hủy sale | Bán/hủy trong `transaction.atomic()`; lưu snapshot. |
| `apps.reports` | Dashboard, report, export | Chỉ tính sale hoàn thành; ngày theo `Asia/Ho_Chi_Minh`. |
| `shop_hoa_thuan` | Settings, runtime, server, runner, version | Server không tự migrate hoặc thiết lập PIN. |

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

Trang **Thiết bị và sao lưu** không lưu cố định địa chỉ LAN. Mỗi lần mở và mỗi 15 giây khi trang
đang hiển thị, server đọc lại SSID/adapter Wi-Fi và IPv4 private hiện tại; endpoint live dùng
`never_cache`, còn QR được tạo lại từ URL snapshot mới. Trên Windows, nếu không đọc được adapter
thì dùng fallback private IPv4 discovery.

## Consistency và concurrency

- Nhập, trừ, đặt lại tồn và hoàn tồn đều tạo `InventoryMovement`.
- Sale tạo `Sale`, `SaleItem`, trừ tồn và movement trong một transaction; lỗi ở bất cứ dòng nào
  rollback toàn bộ.
- Hủy sale chỉ hợp lệ một lần, có lý do và tạo `sale_return`.
- Server tính lại subtotal, discount và total; không tin tổng từ client.
- Idempotency ràng buộc `(client_key, operation, key)` cùng fingerprint: retry cùng payload trả kết
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
hay thiết lập PIN.

## Bảo mật, media, health và log

- CSRF và browser session HTTP-only; `SHOP_USE_HTTPS=true` chỉ khi HTTPS thực có.
- Không có account application, luồng xác thực người dùng, route đăng nhập hay admin site.
  Migration tương thích chỉ chuyển khóa replay cũ thành browser key; không tự xóa bảng lịch sử
  còn lại vì đó là thao tác schema phá hủy và phải có backup/retirement plan riêng.
- `DJANGO_ALLOWED_HOSTS` không chấp nhận wildcard; dùng localhost, hostname/IP LAN phát hiện
  hoặc host cấu hình rõ.
- Cost/PIN hash không ra response/context/export/log khi cost lock đóng.
- Product media chỉ phục vụ dưới media root và chỉ JPEG/PNG/WebP decode hợp lệ; LAN access là
  một quyết định vận hành, không phải access-control boundary.
- Log server, security, business, backup, restore, update, service xoay tối đa 5 file/category;
  filter che PIN, session, CSRF, authorization, secret và cost price.
- `/health/` nhẹ, không trả stack trace/path/secret/dữ liệu nghiệp vụ; phản ánh version,
  database, maintenance và schema compatibility.

## Mô hình truy cập LAN

Mọi thiết bị nằm trong LAN được cấu hình có thể mở và thực hiện nghiệp vụ: catalog, tồn kho,
bán hàng, hủy giao dịch, báo cáo và backup theo các ràng buộc PIN tương ứng. Browser session
chỉ giữ trạng thái mở khóa giá vốn và browser key chống gửi trùng; nó **không** đại diện danh tính
hay quyền riêng theo người dùng.

Vì vậy, biên bảo vệ vận hành là mạng tin cậy: chỉ firewall profile Private, không port-forward,
không public tunnel và không dùng Wi-Fi khách/công cộng. PIN chỉ bảo vệ giá vốn, không thay thế
kiểm soát truy cập cho dữ liệu bán hàng/tồn kho. Khi nghi ngờ một thiết bị đã truy cập trái phép,
ngắt thiết bị khỏi LAN, kiểm tra log, khóa PIN giá vốn và thay PIN; không dựa vào việc xóa cookie
để thu hồi quyền nghiệp vụ.

Version authored duy nhất là `pyproject.toml`, được bundle vào executable để UI, health, backup
manifest và artifact dùng cùng giá trị.

## Trạng thái Windows

PyInstaller native server, migration, health, launcher, update, backup và restore utilities đã
build; server/migration/health smoke và WinSW/SCM/firewall/recovery test data PASS trên Windows.
Clean install, reboot, restore/update native và thiết bị thật vẫn cần evidence; xem
[roadmap](DELIVERY_ROADMAP.md) và [known limitations](KNOWN_LIMITATIONS.md).
