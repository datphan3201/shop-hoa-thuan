# Shop Hoà Thuận

Ứng dụng quản lý nội bộ cho shop quần áo: sản phẩm theo size, tồn kho, bán hàng, doanh thu,
báo cáo và khóa bảo vệ giá vốn. Kiến trúc là Django monolith, Django Templates và HTMX; không
có dependency cloud bắt buộc.

Hiện đã có quản lý loại mặt hàng, sản phẩm nhiều size, ảnh/thumbnail, tìm kiếm/lọc và
điều chỉnh tồn kho nguyên tử kèm lịch sử.

Giá vốn mặc định bị khóa bằng PIN riêng ở server. Khi khóa, giao diện không nhận giá vốn
hoặc lợi nhuận; phiên mở khóa tự hết hạn và biến mất khi đóng trình duyệt.

## Trạng thái

Phase 1–8 đã hoàn thành trong WSL. Phase 9–12 đã có source, test nền tảng và artifact Windows;
native server/migration/health smoke đã đạt, nhưng WinSW/SCM/firewall, clean-install,
restore/update native và thiết bị thật còn chờ validation có quyền Administrator hoặc thiết bị.
Phase 13 hiện là `CONDITIONALLY ACCEPTED` cho internal build validation, chưa phải
`ACCEPTED FOR PRODUCTION RELEASE`.

## Tài liệu

- [Kiến trúc](docs/ARCHITECTURE.md): thành phần, runtime data, lock, security và deployment.
- [Data model](docs/DATA_MODEL.md): schema nghiệp vụ, constraint, snapshot và lifecycle.
- [Use case](docs/USE_CASES.md): luồng thiết lập, catalog, tồn, bán, hủy, report và mobile.
- [Roadmap phát hành](docs/DELIVERY_ROADMAP.md): trạng thái, việc tiếp theo và cách thực hiện.
- [Chất lượng và rủi ro](docs/QUALITY_AND_RISK.md): quality gate, deployment warning, risk.
- [Vận hành nghiệp vụ](docs/OPERATIONS.md), [runtime production](docs/PRODUCTION_RUNTIME.md),
  [Mobile/PWA](docs/MOBILE_PWA.md), [Windows Service](docs/WINDOWS_SERVICE.md).

## Phát triển trong WSL

Yêu cầu duy nhất cho môi trường phát triển là Ubuntu WSL và `uv`.

```bash
cd ~/code/shop-hoa-thuan
uv sync
uv run python manage.py migrate
uv run python manage.py runserver 127.0.0.1:2505
```

Mở `http://127.0.0.1:2505/`.

Ứng dụng dùng trực tiếp trong LAN; mọi thiết bị trong mạng được cấu hình có thể sử dụng.
PIN giá vốn vẫn bắt buộc để xem hoặc sửa dữ liệu nhạy cảm.

## Cấu hình

Sao chép `.env.example` thành `.env` cho môi trường phát triển nếu cần. Ứng dụng không
tự đọc file `.env`; các giá trị phải được export bởi shell hoặc launcher để tránh thêm
dependency không cần thiết.

Các biến chính:

- `DJANGO_DEBUG`
- `DJANGO_SECRET_KEY`
- `DJANGO_ALLOWED_HOSTS`
- `SHOP_DATA_DIR`
- `SHOP_SERVER_HOST`
- `SHOP_SERVER_PORT` — mặc định `2505` cho bản production.

## Dữ liệu

Development mặc định dùng `.data/`. Bản Windows sẽ dùng thư mục dữ liệu dùng chung bên
ngoài thư mục cài đặt. Database, media, backup và secret thật không được commit.

Trang **Thiết bị và sao lưu** có thể tạo và tải file backup nhất quán gồm SQLite, media
và manifest; restore có xác nhận và rollback nền tảng đã có test. Không dùng dữ liệu thật cho
failure injection và phải kiểm thử restore trên bản sao trước khi vận hành production.

## Kiểm tra

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
```

Xem [PROGRESS.md](PROGRESS.md) để biết checklist phase, evidence và trạng thái chính thức.

## Đóng gói Windows

Khung phát hành nằm trong `packaging/` và `scripts/build_windows.ps1`. PyInstaller phải chạy
native trên Windows, không cross-compile từ WSL. Bản build hiện tại đã tạo
`dist/installer/ShopHoaThuan-Setup-1.1.0.exe` cùng server, migration, health, launcher,
backup, restore và update utility. Máy đích không cần Python/uv/Git/Node; clean-install,
service thật và acceptance cuối vẫn phải hoàn thành trước khi phát hành production.

Địa chỉ local dự kiến sau khi hoàn thiện Phase 9 là
`http://shophoathuan.local:2505`. Nếu mDNS không khả dụng, trang thiết bị sẽ hiển thị
`http://<IP-LAN>:2505` và mã QR làm phương án dự phòng. Tên `.local` chỉ được quảng bá
trong LAN, không đăng ký DNS công cộng và không tự mở ứng dụng ra Internet.
