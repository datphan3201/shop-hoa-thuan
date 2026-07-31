# Windows Service và launcher

Service production dùng WinSW, tên hiển thị **Shop Hoà Thuận Server** và chỉ chạy
`ShopHoaThuanServer.exe`. Entry point server không chạy migration, first-run hay seed data; schema
không tương thích khiến server thoát bằng `SHOP-SERVER-003`.

Service chạy Waitress trên cổng cấu hình `SHOP_SERVER_PORT` (mặc định 2505), lấy lock theo data
directory và ghi log ở `%ProgramData%\Shop Hoa Thuan\logs`. `DJANGO_ALLOWED_HOSTS` không được
set wildcard trong XML; runtime thêm localhost, hostname và IPv4 LAN phát hiện được hoặc dùng
host được cấu hình rõ ràng.

`ShopHoaThuanLauncher.exe` chỉ gọi health loopback, yêu cầu Service Control Manager khởi động
service nếu cần, chờ hữu hạn và mở trình duyệt. Nó không spawn Waitress hoặc Python server.

## Integration test cần Administrator

Sau khi Phase 10 tạo `dist\ShopHoaThuan\ShopHoaThuanServer.exe` và có WinSW x64 đã xác minh,
mở PowerShell **Run as administrator** và chạy đúng một script:

```powershell
C:\Projects\ShopHoaThuan\scripts\windows\phase9_test_service.ps1 `
  -AppRoot C:\Projects\ShopHoaThuan\dist\ShopHoaThuan `
  -WinSwPath C:\Projects\ShopHoaThuan\packaging\vendor\WinSW-x64.exe
```

Script chỉ tạo `ShopHoaThuanTestServer`, firewall rule `Shop Hoa Thuan Test LAN 2505` trên
profile Private và `%ProgramData%\Shop Hoa Thuan Test`. Nó không đụng service, firewall rule hay
dữ liệu production. Dọn lại bằng:

```powershell
C:\Projects\ShopHoaThuan\scripts\windows\phase9_test_service.ps1 `
  -AppRoot C:\Projects\ShopHoaThuan\dist\ShopHoaThuan `
  -WinSwPath C:\Projects\ShopHoaThuan\packaging\vendor\WinSW-x64.exe -Cleanup
```

Cleanup giữ test data để điều tra; chỉ xóa sau khi đã xác minh đúng đường dẫn và không cần log.
