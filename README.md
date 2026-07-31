# Shop Hoà Thuận

Ứng dụng quản lý nội bộ cho một chủ shop quần áo: sản phẩm theo size, tồn kho, bán hàng,
doanh thu, báo cáo và khóa bảo vệ giá vốn.

Hiện đã có quản lý loại mặt hàng, sản phẩm nhiều size, ảnh/thumbnail, tìm kiếm/lọc và
điều chỉnh tồn kho nguyên tử kèm lịch sử.

Giá vốn mặc định bị khóa bằng PIN riêng ở server. Khi khóa, giao diện không nhận giá vốn
hoặc lợi nhuận; phiên mở khóa tự hết hạn và biến mất khi đăng xuất/đóng trình duyệt.

## Trạng thái

Phase 4 đã hoàn thành: sản phẩm, tồn kho, khóa giá vốn và bán/hủy giao dịch đã có kiểm thử.
Không dùng cho dữ liệu thật cho đến khi Phase 13 được chứng nhận trên Windows và mobile.

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
và manifest. Chức năng khôi phục có xác nhận sẽ được hoàn thiện và kiểm thử ở Phase 6.

## Kiểm tra

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy .
uv run python manage.py check
uv run python manage.py makemigrations --check --dry-run
uv run pytest
```

Xem [PROGRESS.md](PROGRESS.md) để biết kế hoạch và tiến độ chi tiết.

## Đóng gói Windows

Khung phát hành nằm trong `packaging/` và `scripts/build_windows.ps1`. PyInstaller phải
chạy trên Windows (không thể tạo file `.exe` bằng cách cross-compile từ WSL). Bộ cài hoàn
chỉnh sẽ được tạo từ Phase 10 và chỉ phát hành sau chứng nhận Phase 13; máy shop không cần
cài Python hoặc công cụ phát triển.

Địa chỉ local dự kiến sau khi hoàn thiện Phase 9 là
`http://shophoathuan.local:2505`. Nếu mDNS không khả dụng, trang thiết bị sẽ hiển thị
`http://<IP-LAN>:2505` và mã QR làm phương án dự phòng. Tên `.local` chỉ được quảng bá
trong LAN, không đăng ký DNS công cộng và không tự mở ứng dụng ra Internet.
