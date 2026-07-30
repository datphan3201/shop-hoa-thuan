# AGENTS.md

## Phạm vi

Các hướng dẫn này áp dụng cho toàn bộ repository Shop Hoà Thuận.

## Môi trường bắt buộc

- Làm việc trong Ubuntu WSL tại `/home/thanhdat/code/shop-hoa-thuan`.
- Dùng `~/.local/bin/uv`; không dùng Python, pip, Node.js hay toolchain từ Windows.
- Dùng Python 3.12 và virtualenv riêng của project tại `.venv`.
- Không dùng shared venv `~/.venvs/ai-engineering`.
- Không thêm Docker, PostgreSQL, Redis, React, Next.js, SPA hoặc backend riêng.
- Không commit secret, database thật, media thật, backup thật hay thông tin đăng nhập.

## Kiến trúc

- Django monolith, Django Templates và HTMX.
- SQLite là nguồn dữ liệu duy nhất ở phiên bản đầu.
- Bootstrap 5, HTMX và Chart.js phải được phục vụ local; không phụ thuộc CDN ở bản cài.
- Dữ liệu thay đổi khi vận hành nằm ngoài thư mục cài đặt:
  - database;
  - ảnh và thumbnail;
  - backup;
  - log và secret cục bộ.
- Mọi thay đổi tồn kho và giao dịch bán/hủy phải chạy trong `transaction.atomic()`.
- Không sửa trực tiếp `ProductVariant.quantity` ngoài inventory service.
- Tiền dùng số nguyên (`PositiveBigIntegerField`), không dùng float/decimal.
- Timestamp lưu UTC với `USE_TZ=True`; hiển thị theo `Asia/Ho_Chi_Minh`.
- Giá vốn bị khóa ở server: khi khóa, queryset/context/response không được chứa giá vốn
  hoặc số liệu suy ra từ giá vốn.

## Quy ước code

- Type hints cho code nghiệp vụ.
- Views mỏng; validation ở forms và services; ràng buộc quan trọng ở database.
- Dùng snapshot cho lịch sử bán hàng.
- Không xóa cứng category, product hoặc variant đã được tham chiếu.
- Giao diện và thông báo hướng đến người dùng đều bằng tiếng Việt.
- Migration phải được commit cùng thay đổi model.
- Test lỗi hồi quy cho mọi bug nghiệp vụ đã sửa.

## Lệnh kiểm tra

Chạy trước mỗi commit phase:

```bash
~/.local/bin/uv run ruff format --check .
~/.local/bin/uv run ruff check .
~/.local/bin/uv run mypy .
~/.local/bin/uv run python manage.py check
~/.local/bin/uv run python manage.py makemigrations --check --dry-run
~/.local/bin/uv run pytest
```

## Git

- Giữ commit theo phase, message rõ ràng.
- Không sửa hoặc xóa thay đổi không liên quan của người dùng.
- Cập nhật `PROGRESS.md` sau mỗi phase.
