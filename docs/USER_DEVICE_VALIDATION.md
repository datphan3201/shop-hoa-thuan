# User/device validation

Chỉ các bước dưới đây cần người dùng hoặc môi trường thiết bị thật. Không yêu cầu người dùng
chạy code hoặc test tự động.

## Windows elevated service test

- Chuẩn bị: xác nhận `C:\Projects\ShopHoaThuan` không chứa data thật; có native artifact.
- Thao tác: mở PowerShell **Run as administrator**, chạy script được ghi trong
  `docs/WINDOWS_SERVICE.md`.
- Mong đợi: service test chạy, `/health/` đạt trước/sau kill process, firewall chỉ Private,
  cleanup gỡ service/rule test.
- Log: giữ `%ProgramData%\Shop Hoa Thuan Test\logs` nếu FAIL.
- PASS/FAIL: chỉ PASS khi script tự xác nhận tất cả bước; không dùng data production.
- Phục hồi: chạy cùng script với `-Cleanup`; không xóa data test trước khi review log.

## Clean Windows install

- Chuẩn bị: Windows 10/11 x64 sạch hoặc VM/Sandbox, không Python/uv/Git/Node.
- Thao tác: chạy installer, kiểm tra shortcut, service, health, reinstall và uninstall mặc định.
- Mong đợi: ProgramData giữ database/media/config/PIN; app nằm ở Program Files; không console.
- Log: installer log và `%ProgramData%\Shop Hoa Thuan\logs`.
- PASS/FAIL: cài mới, reboot, reinstall và uninstall giữ data đều PASS.
- Phục hồi: không chọn xóa dữ liệu nếu chưa có backup xác minh.

## Điện thoại thật

- Chuẩn bị: điện thoại cùng Wi-Fi Private với host; không dùng Wi-Fi khách.
- Thao tác: mở URL từ trang Thiết bị, tạo/sửa sản phẩm, upload camera, điều chỉnh kho, bán
  hàng, khóa/mở PIN giá vốn và Add to Home Screen.
- Mong đợi: không overflow ngang, touch target dùng được, double-submit không tạo giao dịch đôi,
  camera đúng orientation, không lộ giá vốn khi khóa.
- Log: ghi thời điểm và mã sale; không chụp/đính kèm PIN, secret hoặc dữ liệu nhạy cảm.
- PASS/FAIL: ghi từng viewport/device và lỗi cụ thể.
- Phục hồi: dừng thao tác ghi khi mất mạng; tra idempotency/status trước khi retry.
