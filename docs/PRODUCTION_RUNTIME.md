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
application tree và dọn staging trong mọi exception path. Bản update 1.1.0 chạy worker từ bản sao
ngoài `Program Files`, áp dụng lại firewall LAN-scoped trên Private/Public và cập nhật snapshot
SSID/IP/QR trên UI. Bản `1.2.0` áp dụng firewall LAN-scoped cho cả profile Public và Private.

## Giới hạn Windows

Lease/maintenance đã có test WSL và test process native trong nhóm test Windows. Native server,
migration, health, WinSW, shutdown/restart SCM, crash recovery và LAN firewall trên Private/Public đã đạt trên
test data Windows. ACL production, clean installer, reboot, restore/update native và LAN device
vẫn cần evidence; không coi các mục này là PASS khi chưa có evidence.
