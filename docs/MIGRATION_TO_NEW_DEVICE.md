# Chuyển sang máy mới

1. Trên máy cũ, tạo backup từ giao diện và chờ thông báo hoàn tất.
2. Copy nguyên file ZIP hoàn chỉnh sang máy mới bằng USB hoặc kênh lưu trữ tin cậy.
3. Cài Shop Hoà Thuận trên máy mới; không cần Python, Git, uv hoặc Node.js.
4. Khởi động service, mở giao diện và thiết lập PIN nếu installation mới chưa có PIN.
5. Mở **Thiết bị và sao lưu**, chọn file ZIP, kiểm tra manifest rồi nhập `KHÔI PHỤC`.
6. Xác minh số sản phẩm, tổng tồn, giao dịch, doanh thu, ảnh và thiết lập PIN.
7. Chỉ cho điện thoại truy cập sau khi firewall đã ở profile Private và máy mới nằm trong LAN
   tin cậy.

Không copy live database khi service đang chạy. Không xóa dữ liệu máy cũ cho đến khi restore,
health và smoke test trên máy mới đạt.
