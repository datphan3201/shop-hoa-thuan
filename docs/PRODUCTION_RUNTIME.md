# Runtime production và release operations

## Một server và maintenance

`config/server.lock` là lease theo data directory. Lease chứa PID, operation ID và thời điểm lấy
lock; process mới chỉ thay lease khi PID chủ cũ không còn sống. Server luôn giải phóng lease qua
`finally`. `config/maintenance.json` dùng cùng nguyên tắc và active write được đánh dấu bằng các
file ngắn hạn trong `config/active-writes`. Maintenance chặn write mới, chờ marker hiện hữu hết
hoặc timeout, rồi tự giải phóng state khi lỗi.

## Runner

`server.py` không chạy migrate, seed hay thiết lập PIN. `migrate_runtime` là runner riêng dành
cho installer/updater. Server kiểm tra migration graph trước khi listen và trả mã
`SHOP-SERVER-003` khi schema chưa tương thích.

## Cấu hình và log

Version runtime đọc từ `pyproject.toml`; health, UI context và manifest backup dùng cùng giá trị.
`DJANGO_ALLOWED_HOSTS` không chấp nhận wildcard. HTTP LAN giữ secure-cookie/redirect tắt; chỉ đặt
`SHOP_USE_HTTPS=true` khi reverse proxy/Tailscale đã cung cấp HTTPS. Log xoay tối đa 5 file mỗi
nhóm trong `logs/`: server, security, business, backup, restore, update và service. Filter chung
che PIN, secret, CSRF/session/authorization và cost price.

## Backup, restore và update

`ShopHoaThuanBackup.exe` và `ShopHoaThuanRestore.exe` là GUI native; chúng khởi tạo cùng runtime
config, lấy maintenance lock và không yêu cầu terminal. Restore validate ZIP trước khi tạo
pre-restore backup. `ShopHoaThuanUpdate.exe` chỉ nhận package có manifest/checksum, thay toàn bộ
application tree và dọn staging trong mọi exception path.

## Giới hạn Windows

Lease/maintenance được test trên Linux local filesystem. WinSW, shutdown SCM, ACL ProgramData,
installer và PyInstaller chỉ được chứng nhận ở Phase 9–10 trên Windows sạch.
