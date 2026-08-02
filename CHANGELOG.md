# Changelog

## 1.2.0

- Cho phép truy cập LAN khi Windows đang ở profile mạng `Public` hoặc `Private`.
- Firewall chỉ cho `ShopHoaThuanServer.exe`, TCP `2505` và `LocalSubnet`; không mở toàn bộ Public
  ra Internet.
- Update runner áp dụng lại chính sách firewall LAN sau khi thay application tree.

## 1.1.0

- Cập nhật trang **Thiết bị và sao lưu** tự động theo trạng thái Wi-Fi hiện tại.
- Hiển thị SSID và adapter Wi-Fi đang kết nối trên Windows.
- Ưu tiên địa chỉ IPv4 của adapter Wi-Fi hiện tại khi tạo URL và mã QR.
- Tự làm mới địa chỉ LAN và mã QR sau mỗi 15 giây hoặc khi quay lại trang.
- Gói update áp dụng firewall rule Private và chạy updater từ bản sao ngoài thư mục ứng dụng,
  tránh khóa file khi thay application tree.
- Không thay đổi schema hoặc dữ liệu nghiệp vụ.
