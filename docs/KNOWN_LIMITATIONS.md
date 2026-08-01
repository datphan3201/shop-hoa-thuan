# Known limitations

## Chưa thể xác minh trong môi trường hiện tại

- Service Control Manager, WinSW, crash recovery và firewall Private đã PASS trên test data bằng
  PowerShell Administrator; clean-install, production ACL và reboot/autostart vẫn chưa có evidence.
- Reboot/autostart, clean Windows install, reinstall/repair/uninstall và ACL ProgramData chưa
  có evidence trên máy sạch.
- Điện thoại thật: LAN, camera orientation, touch UX, PWA Add to Home Screen và mất mạng.
- Tailscale/HTTPS/mDNS/hostname resolution trên Android/iOS.
- Update/rollback failure injection khi service đang chạy native.
- Full pytest Windows qua cầu WSL có thể bị console bridge gửi `KeyboardInterrupt`; các nhóm
  operations, runner/runtime, update và Windows asset đã pass riêng. Cần chạy full suite trong
  PowerShell native ổn định hoặc Windows CI trước khi ghi nhận Windows full PASS.

## Giới hạn thiết kế

- Bản đầu dùng SQLite một host; không đặt database trên cloud sync, NAS, USB hoặc network share.
- HTTP LAN vẫn có thể bị nghe lén; chỉ dùng Private LAN tin cậy hoặc cấu hình HTTPS/Tailscale.
- Không có account/password nghiệp vụ; PIN chỉ khóa giá vốn, không phải authorization cho các
  thao tác bán hàng/tồn kho.
- Gói update local chưa có chữ ký số; checksum và nguồn file cục bộ là điều kiện preflight.
