# Known limitations

## Chưa thể xác minh trong môi trường hiện tại

- Service Control Manager, WinSW, crash recovery, firewall LAN-scoped Private/Public và native installer
  service/health/database smoke đã PASS trên Windows test.
- Reboot/autostart, reinstall/repair/uninstall giữ dữ liệu, production ACL và clean Windows
  acceptance đầy đủ vẫn chưa có evidence.
- Firewall production rule hiện mới có source fix; artifact Windows đang cài chưa chứa helper này.
  Sau rebuild phải xác minh rule áp dụng cho `Private/Public`, chỉ giới hạn `LocalSubnet`, và điện
  thoại truy cập được qua LAN.
- Lần clean-install đầu tiên bị chặn bởi hostname Windows tự phát hiện có dấu gạch dưới; source
  đã sửa, rebuild và native health smoke sau sửa đã PASS.
- Điện thoại thật: LAN, camera orientation, touch UX, PWA Add to Home Screen và mất mạng.
- Tailscale/HTTPS/mDNS/hostname resolution trên Android/iOS.
- Update/rollback failure injection khi service đang chạy native.
- Full pytest Windows qua cầu WSL có thể bị console bridge gửi `KeyboardInterrupt`; các nhóm
  operations, runner/runtime, update và Windows asset đã pass riêng. Cần chạy full suite trong
  PowerShell native ổn định hoặc Windows CI trước khi ghi nhận Windows full PASS.

## Giới hạn thiết kế

- Bản đầu dùng SQLite một host; không đặt database trên cloud sync, NAS, USB hoặc network share.
- HTTP LAN vẫn có thể bị nghe lén; chỉ dùng LAN tin cậy, kể cả khi Windows đang ở profile Public,
  hoặc cấu hình HTTPS/Tailscale.
- Không có account/password nghiệp vụ; PIN chỉ khóa giá vốn, không phải authorization cho các
  thao tác bán hàng/tồn kho.
- Gói update local chưa có chữ ký số; checksum và nguồn file cục bộ là điều kiện preflight.
