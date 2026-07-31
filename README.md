# Shop Hoà Thuận

Ứng dụng quản lý nội bộ cho shop quần áo: sản phẩm theo size, tồn kho, bán hàng, doanh thu,
báo cáo và khóa bảo vệ giá vốn. Kiến trúc là Django monolith, Django Templates và HTMX; không
có dependency cloud bắt buộc.

Hiện đã có quản lý loại mặt hàng, sản phẩm nhiều size, ảnh/thumbnail, tìm kiếm/lọc và
điều chỉnh tồn kho nguyên tử kèm lịch sử.

Giá vốn mặc định bị khóa bằng PIN riêng ở server. Khi khóa, giao diện không nhận giá vốn
hoặc lợi nhuận; phiên mở khóa tự hết hạn và biến mất khi đăng xuất/đóng trình duyệt.

## Trạng thái

Phase 1–8 đã hoàn thành; Phase 9 (Windows Service, launcher và LAN) đang triển khai. Native
Windows server đã smoke-test `/health/`, nhưng gate WinSW/SCM/firewall, installer,
backup/restore, update/rollback, clean Windows và thiết bị thật chưa đạt. Không dùng dữ liệu
thật cho đến khi Phase 13 có chứng nhận release.

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

Lần đầu sử dụng, mở `/setup/` để tạo tài khoản chủ shop. Sau khi tài khoản được tạo,
route này tự đóng và không thể dùng để đăng ký thêm.

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
và manifest. Khôi phục có xác nhận sẽ được hoàn thiện và kiểm thử ở Phase 11.

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
native trên Windows, không cross-compile từ WSL. Máy đích sẽ không cần Python/uv/Git/Node; bộ
cài hoàn chỉnh vẫn là công việc Phase 10 và chỉ phát hành sau chứng nhận Phase 13.

Địa chỉ local dự kiến sau khi hoàn thiện Phase 9 là
`http://shophoathuan.local:2505`. Nếu mDNS không khả dụng, trang thiết bị sẽ hiển thị
`http://<IP-LAN>:2505` và mã QR làm phương án dự phòng. Tên `.local` chỉ được quảng bá
trong LAN, không đăng ký DNS công cộng và không tự mở ứng dụng ra Internet.
