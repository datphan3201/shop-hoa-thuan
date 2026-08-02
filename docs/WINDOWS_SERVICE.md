# Windows Service và launcher

Service production dùng WinSW, tên hiển thị **Shop Hoà Thuận Server** và chỉ chạy
`ShopHoaThuanServer.exe`. Entry point server không chạy migration, thiết lập PIN hay seed data; schema
không tương thích khiến server thoát bằng `SHOP-SERVER-003`.

Service chạy Waitress trên cổng cấu hình `SHOP_SERVER_PORT` (mặc định 2505), lấy lock theo data
directory và ghi log ở `%ProgramData%\Shop Hoa Thuan\logs`. `DJANGO_ALLOWED_HOSTS` không được
set wildcard trong XML; runtime thêm localhost, hostname và IPv4 LAN phát hiện được hoặc dùng
host được cấu hình rõ ràng.

Installer cấu hình firewall bằng helper PowerShell idempotent. Rule `Shop Hoa Thuan LAN 2505`
chỉ cho phép `ShopHoaThuanServer.exe` trên profile `Private`; không mở profile `Public` và không
mở port router. Uninstaller gỡ đúng rule này.

`ShopHoaThuanLauncher.exe` chỉ gọi health loopback, yêu cầu Service Control Manager khởi động
service nếu cần, chờ hữu hạn và mở trình duyệt. Nó không spawn Waitress hoặc Python server.

## Trạng thái và integration test cần Administrator

Native `ShopHoaThuanServer.exe` đã smoke-test `/health/`. Script integration đã chạy elevated
trên test data và đạt WinSW install/start, health, kill-process recovery, stop/start lại và
firewall Private; service/rule được cleanup thành công. Đây là PASS cho test data, chưa phải
clean-install/reboot/production-data acceptance. Không dùng script này với
`%ProgramData%\Shop Hoa Thuan` production.

Sau khi Phase 10 tạo `dist\ShopHoaThuan\ShopHoaThuanServer.exe` và có WinSW x64 đã xác minh,
mở PowerShell **Run as administrator** và chạy đúng một script:

```powershell
& "C:\Projects\ShopHoaThuan\scripts\windows\phase9_test_service.ps1" `
  -AppRoot "C:\Projects\ShopHoaThuan\dist\ShopHoaThuan" `
  -WinSwPath "C:\Projects\ShopHoaThuan\packaging\vendor\WinSW-x64.exe" `
  -ProjectRoot "C:\Projects\ShopHoaThuan" `
  -PythonExe "C:\Projects\ShopHoaThuan\.venv-windows\Scripts\python.exe"
```

Script chỉ tạo `ShopHoaThuanTestServer`, firewall rule `Shop Hoa Thuan Test LAN 2505` trên
profile Private và `%ProgramData%\Shop Hoa Thuan Test`. Nó explicit migrate database test bằng
toolchain development (không phải service startup), kiểm tra health, kill process test để xác
minh WinSW recovery, rồi tự gỡ service/rule. Nó không đụng service, firewall rule hay dữ liệu
production. Data/log test được giữ để điều tra. Dọn thủ công khi cần bằng:

```powershell
& "C:\Projects\ShopHoaThuan\scripts\windows\phase9_test_service.ps1" `
  -AppRoot "C:\Projects\ShopHoaThuan\dist\ShopHoaThuan" `
  -WinSwPath "C:\Projects\ShopHoaThuan\packaging\vendor\WinSW-x64.exe" `
  -ProjectRoot "C:\Projects\ShopHoaThuan" `
  -PythonExe "C:\Projects\ShopHoaThuan\.venv-windows\Scripts\python.exe" -Cleanup
```

Cleanup giữ test data để điều tra; chỉ xóa sau khi đã xác minh đúng đường dẫn và không cần log.

### Kết quả gần nhất

- `phase9_test_service.ps1`: PASS trên `C:\ProgramData\Shop Hoa Thuan Test`.
- WinSW install/start, `/health/`, kill PID/recovery và stop/start: PASS.
- Firewall rule `Shop Hoa Thuan Test LAN 2505` với profile Private: PASS; rule/service được gỡ.
- Một số dòng tiếng Việt hiển thị sai trong console do code page Windows; không ảnh hưởng
  exit status hoặc kết quả service. Dùng code page UTF-8 khi thu thập log đọc được.
