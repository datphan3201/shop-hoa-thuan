# Tiến độ Shop Hoà Thuận

Cập nhật gần nhất: 2026-08-02

## Trạng thái hiện tại

- Phase 3 — Khóa giá vốn và thống kê tồn: **hoàn thành**.
- Phase 4 — Bán hàng: **hoàn thành**.
- Phase 5 — Dashboard và báo cáo: **hoàn thành**.
- Phase 7 — Chuẩn hóa dữ liệu và deployment: **hoàn thành trong WSL**.
- Phase 8 — mobile-first, PWA và chống gửi trùng: **hoàn thành trong WSL**.
- Phase 9 — Windows Service, launcher và LAN: **service/SCM/recovery PASS; LAN-scoped firewall cho profile Private/Public cần rebuild và LAN device/reboot còn lại**.
- Phase 10 — PyInstaller và installer: **install/service/health/database smoke PASS; LAN-scoped firewall fix cần rebuild, reboot, reinstall và uninstall giữ dữ liệu còn lại**.
- Phase 11 — Backup/restore: **backend, GUI source và WSL restore test PASS; Windows restore thật chưa chạy**.
- Phase 12 — Update/rollback: **đã bổ sung update device access/firewall và updater worker ngoài app tree; native 1.1.0→1.2.0/rollback chưa chạy**.
- Phase 13 — Final acceptance: **đang lập evidence; chưa được production accepted**.

### Trạng thái runtime và địa chỉ truy cập — 2026-08-01

- Lần kiểm tra cuối: `http://127.0.0.1:2505/health/` chưa kết nối vì server/service hiện không
  chạy thường trú. Native server trước đó đã smoke-test PASS trên test data và được dừng sau test;
  không coi việc smoke-test là service production đang hoạt động.
- URL host mặc định khi server được khởi động: `http://127.0.0.1:2505`.
- Địa chỉ LAN phát hiện trên Windows host: `http://192.168.1.182:2505` và
  `http://192.168.1.136:2505`; điện thoại phải cùng mạng với adapter tương ứng.
- Hostname LAN tùy chọn: `http://shophoathuan.local:2505` nếu mDNS trên mạng hỗ trợ.
- Khi service/launcher hoàn thiện, trang **Thiết bị và sao lưu** phải là nguồn hiển thị địa chỉ
  thực tế thay vì giả định một IP cố định.

### Trạng thái thực tế sau lượt build cuối — 2026-08-01

Các commit gần nhất đã push lên branch `bugfix`: `80d286e` (backup/restore GUI), `ead1fa7`
(update package builder và regression tests), `8bda778` (update thay toàn bộ application tree),
`48e895e` (Windows backup validation), `fc1fd46` (đóng SQLite validation handles trên Windows),
`ebe4faf` (hoàn thiện release docs/ignore vendor tool) và `587eae0` (ghi trạng thái địa chỉ server).
Tài liệu nghiệm thu hiện nằm trong `docs/REQUIREMENT_TRACEABILITY_MATRIX.md`,
`docs/FINAL_ACCEPTANCE_REPORT.md`, `docs/KNOWN_LIMITATIONS.md`,
`docs/RELEASE_CHECKLIST.md`, `docs/USER_DEVICE_VALIDATION.md`, `docs/UPDATE.md` và
`docs/RELEASE_PROCESS.md`.

Windows build evidence:

- Windows 11 x64, Python 3.12.10, PyInstaller 6.21.0, Inno Setup 6.7.3.
- `ShopHoaThuanServer.exe`: native `/health/` smoke PASS trên test data.
- `ShopHoaThuanMigration.exe`: migration runner PASS, output Unicode PASS, không tự chạy từ server.
- `ShopHoaThuanHealth.exe`: không có server trả `SHOP-HEALTH-001`, exit code 1 như thiết kế.
- Installer `ShopHoaThuan-Setup-1.0.0.exe`: compile PASS; SHA-256 của build trước lỗi hostname là
  `45B6EF4CF272E020ECC220F1C207737B19B401F83579886515C6B57657C096C6`; hash rebuild cần bổ sung.
- Kích thước artifact baseline 1.0.0: installer 195,550,176 bytes; server 7,599,613 bytes;
  migration 7,603,330 bytes; health 20,147,834 bytes; launcher 32,929,919 bytes;
  update 33,044,818 bytes; backup 33,046,256 bytes; restore 33,046,194 bytes.
- SHA-256 native smoke set: server `B9C0EC6BA302016DFFBB8392FE91B9BE1C2E77AA07A6B68C990253789AB62120`;
  migration `FF3E127320DDA4ACAF956E8D3D4C536C4A532A850A34DB032F05C4ADD3EE2AA2`;
  health `B684D3DB63B9BC58E8239417160121083A9456249931F8A347C37FB9D3716421`.
- Standalone health/launcher/update/backup/restore specs đã nhúng runtime binaries; lỗi thiếu
  `python312.dll` đã được bắt bằng smoke test và sửa.

WSL quality gate sau các thay đổi code/tài liệu: `ruff format --check` PASS (112 files), Ruff
PASS, mypy PASS (88 source files), Django system check PASS, migration check PASS và full pytest
PASS: **137 passed, 1 warning**. Warning pytest còn lại là warning kỹ thuật của
`override_settings(DATABASES=...)` trong restore test, không phải test fail.

Django deployment check với production test env (`DEBUG=false`, secret test dài, hosts
`localhost,127.0.0.1,192.168.1.69`) PASS với đúng 4 warning có chủ đích: `W004`, `W008`, `W012`, `W016`.
`W009` và `W018` chỉ xuất hiện khi chạy nhầm bằng development env và không được chấp nhận
trong build.

Deployment warning phân loại:

- Phải sửa trước release: DEBUG production, `W009`, wildcard `ALLOWED_HOSTS`, secret ngắn,
  schema mismatch, migration ngoài ý muốn và warning build không giải thích được.
- Chấp nhận có điều kiện cho HTTP LAN: `W004`, `W008`, `W012`, `W016`; chỉ dùng LAN tin cậy,
  firewall giới hạn `LocalSubnet` trên profile Private/Public, hoặc bật `SHOP_USE_HTTPS=true`
  khi có HTTPS/Tailscale phù hợp.
- Chỉ xác minh trên Windows/device: ACL production, reboot, clean install, LAN phone,
  camera, Add to Home Screen, native update/rollback.

Windows test evidence sau build cuối:

- `tests/test_operations.py`: **6 passed**.
- `tests/test_runner.py tests/test_runtime.py`: **6 passed**.
- `tests/test_update.py tests/test_windows_service_assets.py`: **18 passed**.
- `phase9_test_service.ps1` chạy elevated: **PASS** — WinSW install/start, `/health/`, kill PID
  recovery, stop/start và firewall LAN trên profile Private/Public; service/rule được cleanup,
  test data được giữ.
- Full pytest WSL baseline: **122 passed, 1 warning**; sau network/update/bootstrap changes: **137 passed, 1 warning**. Full pytest native Windows đã được thử qua cầu
  WSL nhưng console bridge phát `KeyboardInterrupt` sau 101 test; không ghi nhận đó là full
  Windows PASS. Cần chạy lại trong PowerShell/Windows CI native ổn định trước release.
- Output tiếng Việt của một số thông báo WinSW bị mojibake trong console hiện tại do code page;
  đây là vấn đề hiển thị của terminal test, không làm fail service/health/recovery. Có thể chạy
  lại với code page UTF-8 khi cần lưu log đọc được.

Clean-install finding — 2026-08-02:

- Installer 1.0.0 đã đăng ký được `ShopHoaThuanServer`, nhưng `/health/` không mở và database
  không được tạo tại `C:\ProgramData\Shop Hoa Thuan\data\db.sqlite3`.
- WinSW log xác định root cause: hostname Windows tự phát hiện có dấu gạch dưới
  (`SHOP_SERVER_TEST` trong test) bị đưa vào `DJANGO_ALLOWED_HOSTS`, sau đó validation production
  từ chối hostname đó và server thoát trước khi bind cổng.
- Đã sửa `production_allowed_hosts()` để bỏ qua hostname tự phát hiện không hợp lệ; hostname do
  người vận hành cấu hình vẫn bị reject. Đã thêm regression test cho lỗi này.
- Đã rebuild và chạy lại trên Windows test: `ShopHoaThuanServer` ở trạng thái `Running`,
  `/health/` trả HTTP 200 với `status=ok`, `database=true`, `schema=true`, `version=1.0.0`,
  và `C:\ProgramData\Shop Hoa Thuan\data\db.sqlite3` tồn tại.
- Đã phát hiện installer bản đó chưa tạo production firewall rule; source đã bổ sung script
  idempotent tạo rule `Shop Hoa Thuan LAN 2505` trên profile `Private` và `Public`, giới hạn theo
  server executable và `LocalSubnet`, rồi gỡ rule khi uninstall. Cần rebuild installer rồi kiểm tra
  lại trên Windows.
- Hash mới của installer cần được ghi lại từ output `Get-FileHash`; hash cũ ở phần artifact là
  build trước lỗi và không dùng làm release evidence.

Update UI/network fix — 1.1.0:

- Trang device access có endpoint live không cache và tự refresh mỗi 15 giây; QR được tạo lại từ
  URL LAN snapshot mới.
- Windows đọc SSID/adapter bằng `netsh` không mở shell và lấy IPv4 của adapter Wi-Fi hiện tại;
  nếu không lấy được thì fallback về private IPv4 discovery.
- Update package 1.0.0 → 1.1.0 phải được build từ frozen tree có `configure_firewall.ps1`; native
  update và rollback chưa có evidence.
- Updater portable 1.1.0 đọc version đang chạy từ `/health/`, mặc định dùng
  `C:\Program Files\Shop Hoa Thuan` khi chạy ngoài application tree, rồi chuyển rõ version cài
  hiện tại cho update worker. Vì vậy có thể nâng cài đặt 1.0.0 bằng updater mới mà không uninstall;
  cần native Windows test để đóng evidence.

Firewall profile update — 1.2.0:

- Version nguồn duy nhất đã tăng lên `1.2.0` để thay đổi firewall được phát hành qua updater,
  không ghi đè silent cùng version.
- Firewall helper cho phép profile `Private` và `Public`, nhưng chỉ nhận TCP `2505` từ
  `LocalSubnet` và đúng `ShopHoaThuanServer.exe`; không mở toàn bộ Public ra Internet.
- Gói update cần tạo từ frozen tree 1.2.0 với `current_version=1.1.0`, `target_version=1.2.0`;
  native update và rollback chưa có evidence.

### Việc cần làm tiếp theo

1. Trên Windows test hiện tại, reboot rồi kiểm tra service/health tự khởi động; sau đó kiểm tra
   reinstall/repair và
   uninstall mặc định; xác minh ProgramData, service, shortcut và không cần Python.
2. Tạo test package `1.1.0 → 1.2.0` hoặc trực tiếp `1.0.0 → 1.2.0` với manifest khớp
   `/health/`, chạy restore và update/rollback trên data test độc lập; failure injection phải
   chứng minh maintenance, database/media và application tree trở lại trạng thái nhất quán.
3. Chạy checklist thiết bị thật trong `docs/USER_DEVICE_VALIDATION.md`: điện thoại LAN,
   camera, viewport, PWA Add to Home Screen và UX; không đưa dữ liệu thật vào failure injection.
4. Chỉ sau khi các mục trên có evidence mới nâng kết luận Phase 13; nếu còn thiếu thì giữ
   `CONDITIONALLY ACCEPTED`.

Quy ước checklist: `[x]` nghĩa là implementation/test/tài liệu tương ứng đã có evidence;
`[ ]` nghĩa là chưa triển khai hoặc chưa thể xác minh trong môi trường hiện tại. Các ô còn lại
không phải lỗi bị bỏ quên; chúng là điều kiện native Windows, thiết bị thật, performance hoặc
release-hardening chưa đạt.

Không đánh dấu Phase 9–13 hoàn thành cho đến khi các mục BLOCKED có evidence thật. Kết luận hiện
tại là `CONDITIONALLY ACCEPTED` cho internal build validation, không phải production release.

### Cập nhật truy cập LAN — 2026-08-01

- Đã bỏ toàn bộ luồng người dùng: route setup/đăng nhập/đăng xuất, middleware xác thực,
  context, form, runner, admin site và admin registrations. Mọi route nghiệp vụ dùng trực tiếp
  trong LAN; PIN giá vốn vẫn là lớp bảo vệ dữ liệu nhạy cảm theo browser session.
- `IdempotencyRecord` không còn liên kết người dùng. Browser nhận client key ngẫu nhiên trong
  session; unique constraint là `(client_key, operation, key)`.
- Migration tương thích `core.0004` chuyển bản ghi replay cũ sang `legacy-<id>` rồi bỏ cột
  cũ. Đã kiểm tra trên SQLite tạm: record cũ còn nguyên sau upgrade; cài database mới không tạo
  bảng user. Bảng lịch sử còn sót trên installation cũ không tự xóa để tránh thao tác phá hủy.
- Media sản phẩm được dùng trực tiếp trong LAN, nhưng vẫn chỉ nằm dưới media root, decode ảnh
  thật và kiểm tra content type trước khi trả file.
- Gate sau thay đổi: formatter, Ruff, mypy, Django check, migration check và `pytest --create-db`
  đều PASS (`107 passed`).

### Evidence mới nhất Phase 9

- Waitress server entry point giữ single-instance lease, không tự migrate/thiết lập PIN và native
  PyInstaller `onedir` `ShopHoaThuanServer.exe` đã smoke PASS `/health/` trên Windows test data.
- Source launcher, WinSW XML, logging/runtime data config, LAN/device access page và QR đã có.
- Regression packaging đã sửa: import Django trước setup, logging filter dynamic, standard
  library archive, dynamic middleware/app modules và `pyproject.toml` version metadata trong
  frozen bundle.
- WinSW portable 2.12.0.0 được tải từ winget/official GitHub và hash `05B82D…B3A0DA` đã xác minh;
  đây là build/test tool tạm, chưa được commit vào repository.
- Administrator integration service/LAN firewall trên Private/Public/controlled recovery: **PASS** trên test
  data; reboot auto-start, LAN điện thoại và clean Windows vẫn là device validation.

Chi tiết kiến trúc, schema, use case, risk và cách hoàn thành phase tiếp theo ở
`docs/ARCHITECTURE.md`, `docs/DATA_MODEL.md`, `docs/USE_CASES.md`,
`docs/QUALITY_AND_RISK.md` và `docs/DELIVERY_ROADMAP.md`.

## Quyết định kiến trúc

- Django 5.2 LTS trên Python 3.12.
- Django monolith, server-rendered Templates; HTMX chỉ cho tương tác cục bộ.
- SQLite bật foreign keys, WAL và busy timeout để tăng độ bền trên một máy shop.
- Một tiến trình Waitress; các thao tác ghi quan trọng vẫn dùng transaction ngắn.
- Dữ liệu vận hành tách khỏi mã/bộ cài, mặc định:
  - Windows: `%PROGRAMDATA%\Shop Hoa Thuan`;
  - development: `<repository>/.data`;
  - có thể đổi bằng `SHOP_DATA_DIR`.
- Ảnh gốc được resize và tạo thumbnail; không lưu ảnh trong database.
- Bootstrap, HTMX và Chart.js được đóng gói local để ứng dụng hoạt động khi mất Internet.
- PyInstaller `onedir`, Windows Service và Inno Setup là pipeline phát hành; máy shop
  không cần Python, uv, Git hay Node.js.
- Truy cập LAN/Tailscale dùng HTTP ở bản đầu. CSRF, browser session và giới hạn host vẫn
  được bật; hướng dẫn thiết bị cảnh báo chỉ dùng mạng tin cậy vì không có lớp xác thực người dùng.
- Browser session chỉ giữ cost-PIN unlock và idempotency client key, không biểu thị danh tính hay
  quyền nghiệp vụ. Firewall chỉ cho `LocalSubnet` trên Private/Public, không port-forward và kỷ luật
  LAN tin cậy là biên truy cập;
  PIN không thay thế kiểm soát truy cập cho sale/inventory.
- Cổng production cố định mặc định là `2505`. Địa chỉ local ưu tiên là
  `http://shophoathuan.local:2505`; IP LAN và QR luôn là phương án dự phòng.
- `shophoathuan.local` dùng mDNS chỉ trong LAN, không đăng ký DNS công cộng, không mở port
  router và không làm ứng dụng public trên Internet.

## Review kiến trúc production Windows — 2026-07-31

### Thành phần hiện có có thể tiếp tục sử dụng

- Django monolith, Templates, HTMX, Bootstrap và Chart.js local phù hợp máy cấu hình thấp.
- SQLite đã bật foreign keys, WAL, `busy_timeout=20s`, `synchronous=NORMAL` và transaction
  `IMMEDIATE`; các service tồn kho hiện đã dùng transaction.
- Dữ liệu đã được tách khỏi repository bằng `SHOP_DATA_DIR`; ảnh đã được kiểm tra, resize
  và tạo thumbnail.
- Waitress production entry point, PyInstaller `onedir`, WinSW và Inno Setup đã có
  scaffold ban đầu.
- `/health/`, PWA manifest, trang thiết bị và backup bằng SQLite backup API đã có nền tảng.
- CSRF, Django session browser và khóa giá vốn PIN phía server đã được triển khai.

### Khoảng trống phải xử lý trước khi phát hành

| Mức | Hiện trạng | Thay đổi bắt buộc |
|---|---|---|
| P0 | Database hiện là `%PROGRAMDATA%\Shop Hoa Thuan\shop-hoa-thuan.sqlite3`; media và log cũng chưa theo cây thư mục yêu cầu | Chuẩn hóa thành `data\db.sqlite3`, `data\media`, `backups`, `rollback`, `logs`, `config`; hỗ trợ chuyển dữ liệu cũ an toàn và không ghi đè |
| P0 | Server tự chạy migration và seed ở mỗi lần service start | Tách migration thành utility có backup, log và exit code; service bình thường chỉ khởi động ứng dụng |
| P0 | Chưa có maintenance mode, transaction drain hoặc khóa phối hợp backup/update/restore | Tạo cơ chế khóa liên tiến trình và trạng thái maintenance; chặn ghi mới, chờ ghi đang chạy hoàn tất trước khi dừng service |
| P0 | Installer hiện chỉ copy file, đăng ký service và mở URL | Bổ sung thiết lập PIN, firewall LAN-scoped trên Private/Public, health verification, rollback cài đặt và chính sách giữ dữ liệu khi uninstall |
| P0 | Chưa có restore/update/rollback hoạt động end-to-end | Xây GUI utility, preflight, checksum, backup trước thao tác, migration kiểm soát và rollback nguyên tử |
| P0 | Media chỉ được Django phục vụ khi `DEBUG=True` | Thêm cơ chế phục vụ ảnh production an toàn, không để lộ đường dẫn filesystem |
| P1 | `/health/` mới trả boolean database, chưa có version và server time | Trả schema tối thiểu ổn định: status, database, version, server time; không trả path/secret/traceback |
| P1 | Version đang lặp trong `pyproject.toml` và installer | Tạo một nguồn version duy nhất, sinh `version.json` và dùng chung cho health, backup, installer, updater và log |
| P1 | Secret nằm trực tiếp ở data root; log mới có một file chung | Chuyển secret/config vào `config`, tách log theo chức năng, rotation và bộ lọc dữ liệu nhạy cảm |
| P1 | WinSW chưa ghi log đúng `ProgramData\logs`, tên service chưa đúng, chưa có single-instance lock | Chuẩn hóa service `Shop Hoà Thuận Server`, một instance, restart hữu hạn, shutdown an toàn và mã lỗi chẩn đoán |
| P1 | PWA manifest thiếu icon/shortcut; chưa có cache policy | Bổ sung icon/shortcut và service worker chỉ cache static GET; không cache response động hay request ghi |
| P1 | Mobile chủ yếu là bảng cuộn ngang | Chuyển nghiệp vụ chính sang card/list responsive, form một cột và thao tác chạm tối thiểu 44 px |
| P1 | Chưa có idempotency và optimistic concurrency tổng quát | Tạo idempotency record/unique constraint cho thao tác quan trọng và version/`updated_at` guard cho form sửa |
| P1 | Backup manifest mới ở mức cơ bản | Thêm schema/app version, checksum, thống kê dữ liệu, retention, xác minh restore và GUI không dùng terminal |
| P1 | Trang thiết bị chưa phát hiện hostname, LAN/Tailscale hoặc tạo QR | Bổ sung discovery chỉ đọc, URL/QR và hướng dẫn kết nối tiếng Việt |
| P2 | `ALLOWED_HOSTS=*` ở production runner | Sinh danh sách host hợp lệ từ cấu hình máy, `shophoathuan.local`, localhost, hostname và địa chỉ được phát hiện; tài liệu hóa thay đổi mạng |
| P2 | Chưa có bộ tài liệu production yêu cầu | Viết đủ tài liệu cài đặt, host, điện thoại, backup/restore, update, chuyển máy, xử lý lỗi và release |

### Nguyên tắc chuyển đổi

- Không đổi cấu trúc dữ liệu vận hành nếu chưa có backup được xác minh và đường lui.
- Không để service production tự quyết định migration.
- Mỗi thao tác bán hàng, tồn kho, backup, restore và update có một owner/lock rõ ràng.
- Chỉ báo thành công sau khi transaction hoặc snapshot đã commit và được xác minh.
- `C:\Program Files\Shop Hoa Thuan` có thể thay thế; `C:\ProgramData\Shop Hoa Thuan`
  được giữ nguyên mặc định khi cài lại, update, repair và uninstall.
- Phát triển/test tự động tiếp tục trong WSL; tạo và chứng nhận file Windows phải chạy trên
  Windows 10/11 64-bit sạch hoặc Windows CI, vì PyInstaller không cross-compile từ WSL.
- Phase 7–13 không thay thế Phase 4–6. Chỉ bắt đầu triển khai production sau khi nghiệp vụ
  bán hàng, báo cáo và kiểm thử ứng dụng đã đạt gate tương ứng.

## Rủi ro kỹ thuật chính

| Rủi ro | Ảnh hưởng | Biện pháp |
|---|---|---|
| Mất điện khi SQLite đang ghi | Mất/không nhất quán giao dịch | WAL, transaction nguyên tử, foreign keys, backup định kỳ và kiểm tra integrity |
| Hai thao tác bán cùng lúc | Bán quá tồn | Transaction, cập nhật có điều kiện và khóa ghi SQLite ngắn |
| Bộ cài nâng cấp ghi đè dữ liệu | Mất database/media | Dữ liệu nằm ngoài thư mục cài; installer không xóa data dir |
| Máy đổi IP | Điện thoại khó truy cập | Hiển thị địa chỉ LAN/Tailscale trong trang thiết bị; ưu tiên hostname/Tailscale |
| Windows Service không có Desktop session | Không tự mở trình duyệt | Service chỉ chạy server; shortcut Desktop mở URL/PWA riêng |
| Secret/PIN bị lộ | Lộ dữ liệu nhạy cảm | Hash Django, session HTTP-only, không gửi giá vốn khi khóa, giới hạn thử PIN |
| Ảnh dung lượng lớn | Tốn đĩa/RAM | Kiểm tra định dạng/kích thước, resize và thumbnail bằng Pillow |
| Backup không dùng được | Mất khả năng phục hồi | Backup nhất quán gồm DB + media + manifest; kiểm tra ZIP và quy trình restore có xác nhận |
| Truy cập LAN qua HTTP | Cookie có thể bị nghe lén trên mạng xấu | Chỉ mạng tin cậy/Tailscale; tài liệu hóa HTTPS/Tailscale khi truy cập từ xa |
| PyInstaller không cross-compile từ WSL | Không tạo được `.exe` chỉ bằng Linux | Giữ development/test trong WSL; chạy pipeline build cuối trên Windows sạch hoặc Windows CI |

## Kế hoạch triển khai

### Phase 1 — Nền tảng

- [x] Kiểm tra repository và WSL toolchain.
- [x] Chốt Python 3.12, uv và project-local virtualenv.
- [x] Tạo `AGENTS.md`, `PROGRESS.md`, `.env.example`.
- [x] Khởi tạo Django, settings, logging, static/media/data dir.
- [x] Tạo schema cốt lõi, migration và database constraints.
- [x] Bỏ lớp xác thực người dùng; mọi route LAN dùng trực tiếp, giá vốn giữ PIN riêng.
- [x] Tạo layout quản trị, sidebar/header/mobile navigation và route khung.
- [x] Tạo `/health/` không làm lộ dữ liệu.
- [x] Tạo backup nhất quán, kiểm tra archive và giao diện tải backup.
- [x] Tạo khung Waitress, PyInstaller onedir, WinSW và Inno Setup.
- [x] Format, lint, mypy, Django checks, migrations check và tests.
- [x] Commit Phase 1.

Điều kiện hoàn thành: ứng dụng khởi động bằng Waitress, route nghiệp vụ LAN hoạt động,
schema/migration sạch, health check hoạt động, toàn bộ kiểm tra Phase 1 qua.

### Phase 2 — Sản phẩm và tồn kho

- [x] CRUD/soft-disable loại mặt hàng, sản phẩm và size.
- [x] Upload/resize ảnh và tạo thumbnail.
- [x] Tìm kiếm/lọc theo tên, SKU, loại, size, màu, tồn kho và trạng thái.
- [x] Hiển thị size còn hàng, sắp hết và hết hàng từ biến thể hiện tại.
- [x] Inventory service nguyên tử cho nhập, trừ và đặt số lượng.
- [x] Bắt buộc lý do và tạo lịch sử cho mọi biến động.
- [x] Unit/integration tests cho constraints, ảnh, sản phẩm và tồn kho.
- [x] Commit Phase 2.

### Phase 3 — Khóa giá vốn và thống kê tồn

- [x] Thiết lập/đổi PIN và chỉ lưu hash Django.
- [x] Giới hạn 5 lần thử sai và tạm khóa 5 phút.
- [x] Session HTTP-only mở khóa ngắn hạn, browser-session và khóa thủ công.
- [x] Tự khóa khi hết hạn, đăng xuất hoặc đổi thời gian.
- [x] Chặn tạo/sửa giá vốn và tải backup khi đang khóa.
- [x] Defer giá vốn khỏi queryset và không render số liệu nhạy cảm khi khóa.
- [x] Thống kê vốn tồn, giá trị bán, lợi nhuận và tỷ suất theo từng size.
- [x] Unit/integration tests cho PIN, expiry, browser-session clear, rate limit và response.
- [x] Commit Phase 3.

### Phase 4 — Bán hàng

- [x] Màn hình bán hàng tìm theo tên/SKU, lọc loại, chọn đúng size và xem tồn hiện tại.
- [x] Giỏ nhiều size, sửa số lượng/giá thực tế, giảm giá, thanh toán và ghi chú.
- [x] Cảnh báo giá thực tế thấp hơn niêm yết; cảnh báo dưới giá vốn chỉ nhận dữ liệu khi
  khóa giá vốn đã mở.
- [x] Transaction bán hàng nguyên tử, server tính lại tổng, snapshot và trừ kho.
- [x] Retry khóa SQLite ngắn/hữu hạn và test hai giao dịch đồng thời không bán quá tồn.
- [x] Lịch sử có tìm kiếm, lọc ngày/thanh toán/trạng thái, sắp xếp và phân trang.
- [x] Chi tiết giao dịch và hóa đơn in không chứa giá vốn/lợi nhuận.
- [x] Hủy đúng một lần, bắt buộc lý do, hoàn tồn và tạo `sale_return`.
- [x] Test rollback, snapshot bất biến, múi giờ Việt Nam và bảo vệ dữ liệu giá vốn.
- [x] Kiểm tra trực tiếp luồng mở ứng dụng → chọn size → sửa giá → giảm giá → hoàn tất → hóa đơn.
- [x] Commit Phase 4.

Điều kiện hoàn thành: giao dịch nhiều size commit nguyên tử, không bán quá tồn khi cạnh
tranh, lịch sử snapshot không đổi, hủy hoàn tồn đúng một lần và hóa đơn không lộ dữ liệu
nội bộ.

### Phase 5 — Dashboard và báo cáo

- [x] Dashboard, báo cáo theo múi giờ Việt Nam và Chart.js local.
- [x] Doanh thu, bán chạy, tồn thấp/hết và giao dịch gần đây.
- [x] CSV mặc định không có giá vốn; export nhạy cảm chỉ hiện/tải được sau khi mở khóa
  và xác nhận.
- [x] Kiểm thử phân bổ giảm giá, loại trừ giao dịch hủy, ngày theo múi giờ Việt Nam, báo cáo
  không lộ giá vốn khi khóa và CSV.
- [x] Commit Phase 5.

### Phase 6 — Hoàn thiện nghiệp vụ

- [x] Hoàn thiện unit/integration/E2E smoke tests cho sản phẩm, tồn kho, khóa giá vốn, bán
  hàng và báo cáo.
- [x] Audit truy cập LAN trực tiếp, CSRF, session, PIN, dữ liệu nhạy cảm và SQLite integrity
  trong phạm vi app.
- [x] Hoàn thiện empty/error state và tài liệu nghiệp vụ tại `docs/OPERATIONS.md`.
- [x] Chốt schema nghiệp vụ làm đầu vào cho kế hoạch migration production.
- [x] Commit Phase 6.

Điều kiện hoàn thành: E2E nghiệp vụ chính đạt, không còn lỗi nghiêm trọng về tính đúng đắn
giao dịch/tồn kho/báo cáo và schema đã sẵn sàng cho hardening production.

### Phase 7 — Chuẩn hóa dữ liệu và deployment

#### Cấu trúc runtime và dữ liệu

- [x] Tạo module đường dẫn production duy nhất cho:
  - `C:\Program Files\Shop Hoa Thuan` — application files chỉ đọc;
  - `C:\ProgramData\Shop Hoa Thuan\data\db.sqlite3`;
  - `C:\ProgramData\Shop Hoa Thuan\data\media\products`;
  - `backups`, `rollback`, `logs` và `config`.
- [x] Trong development giữ `.data`, nhưng mô phỏng cùng cây thư mục production.
- [x] Viết migration utility một lần cho layout cũ; dùng rename/copy có kiểm tra checksum,
  không xóa nguồn trước khi database mới vượt integrity check.
- [x] Đưa secret key và cấu hình máy vào `config`; áp quyền filesystem phù hợp và không log
  secret.
- [x] Bảo đảm repair/reinstall không tạo lại secret, database hoặc media đã tồn tại.

#### SQLite và điều phối tiến trình

- [ ] Gom cấu hình PRAGMA vào một module được test: foreign keys, WAL, busy timeout,
  synchronous và kiểm tra filesystem local.
- [x] Xác nhận chỉ một Waitress process ghi database; tạo single-instance/process lock.
- [x] Tạo maintenance state và operation lock dùng cho backup, restore, update và migration.
- [x] Theo dõi số transaction ghi đang hoạt động để chặn ghi mới và chờ drain có timeout.
- [ ] Ghi audit event cho các thao tác vận hành quan trọng mà không chứa credential, PIN,
  cookie, secret hoặc toàn bộ giá vốn.

#### Server, media, health, logging và version

- [x] Tách `migrate`/`seed_data` khỏi server startup; tạo migration runner có exit code ổn định.
- [x] Tạo một nguồn version duy nhất dùng chung runtime/health/UI/backup.
- [x] Nâng `/health/` để kiểm tra query database nhẹ và trả status, database, version,
  server time UTC; luôn che traceback/path.
- [x] Phục vụ media LAN an toàn; ảnh sản phẩm chỉ dưới media root, hỗ trợ thumbnail/cache
  header an toàn và không lộ path thật.
- [x] Sinh `ALLOWED_HOSTS`, CSRF trusted origins và listen address từ config được kiểm soát.
- [x] Tách log server, security, business, backup, restore, update và service;
  dùng rotating handler, redaction và mã lỗi thân thiện.

#### Kiểm tra và tài liệu

- [x] Test đường dẫn development, nâng cấp layout cũ, single-instance, maintenance,
  transaction drain, health schema, media LAN, migration tương thích browser key và log redaction.
- [ ] Chạy test SQLite WAL/backup/shutdown trên filesystem local; không hỗ trợ database live
  trong OneDrive, USB, NAS hoặc network share.
- [x] Viết `docs/PRODUCTION_RUNTIME.md` cho runtime/config/lock; tài liệu installer Windows
  đầy đủ vẫn thuộc Phase 9–10.

Điều kiện hoàn thành: application/data tách đúng cây thư mục, service start không tự migrate,
health/version/log đạt contract, media hoạt động ở production, một instance duy nhất và
không mất dữ liệu khi mô phỏng chuyển layout.

### Kết quả Phase 7 — 2026-07-31

- Runtime dùng lease file theo data directory, maintenance state/active-write marker có dọn stale
  PID và timeout; request ghi nhận thông báo bảo trì thay vì báo thành công giả.
- Service không tự migrate/seed; migration là runner riêng. Health che toàn bộ lỗi nội bộ và
  phân biệt `ok`, `maintenance`, `schema_incompatible`, `error`.
- Media LAN chỉ phục vụ JPEG/PNG/WebP dưới media root; version được dùng bởi
  UI context, health và manifest backup. Log xoay/redact theo nhóm runtime.
- 78 test tự động đạt trước test process lease cuối; test process lease đạt riêng. Formatter,
  Ruff, mypy, check và migration check đạt trước thay đổi test cuối.
- `check --deploy` chỉ còn W004/W008/W012/W016 cho HTTP LAN có chủ đích. Không bật HSTS,
  HTTPS redirect hoặc secure cookie khi máy chủ vẫn phục vụ HTTP LAN; bật `SHOP_USE_HTTPS=true`
  khi triển khai HTTPS/Tailscale. W009 xuất phát từ secret test ngắn, không phải cấu hình runtime.
- Tại thời điểm snapshot Phase 7, WinSW/SCM shutdown, ACL ProgramData, installer/PyInstaller
  và filesystem Windows thực vẫn phải chứng nhận trong Phase 9–10. Đây là ghi chú lịch sử;
  Phase 8 hiện đã đạt gate WSL và các phase phát hành đang ở trạng thái nêu tại đầu file.
- Review độc lập đã thay lease stale-rename bằng advisory file lock của OS: cách cũ có TOCTOU có
  thể đổi tên lease mới của process khác. Maintenance state giờ xác định bằng lock đang được giữ,
  không chỉ PID trong JSON nên state đã release không bị báo maintenance do PID vẫn sống.

### Phase 8 — Mobile-first và chỉnh sửa từ điện thoại

#### Responsive và nghiệp vụ mobile

- [ ] Kiểm tra từng route ở 320×568, 360×800, 375×667, 390×844, 412×915, 768×1024
  và desktop ≥1280 px.
- [x] Dùng sidebar desktop; off-canvas/header và bottom navigation mobile cho Tổng quan,
  Sản phẩm, Bán hàng, Tồn kho, Thêm.
- [x] Chuyển bảng rộng của sản phẩm, tồn kho và lịch sử/chi tiết bán hàng thành card/list mobile;
  không dùng cuộn ngang cho thao tác chính.
- [x] Chuẩn hóa form một cột, label trên input, target ≥44×44 px, nút chính full-width và
  modal lớn thành fullscreen/bottom sheet.
- [x] Bảo đảm mobile làm đủ create/edit category, product, variant, inventory, sale,
  cancel, report, unlock cost và backup; không ẩn thao tác ghi.
- [ ] Tối ưu POS cho cả bàn phím desktop và chạm mobile, giữ form khi mạng lỗi.

#### Ảnh, concurrency và chống gửi trùng

- [x] Upload camera/thư viện với preview, xử lý EXIF orientation, resize,
  nén và thumbnail ở server.
- [x] Xác minh decode ảnh thật, pixel/file limit, tên file an toàn;
  file tạm; không tạo product nửa hoàn chỉnh.
- [x] Thêm optimistic concurrency bằng revision tăng dần cho form
  sửa; trả thông báo xung đột tiếng Việt thay vì ghi đè.
- [x] Thiết kế idempotency record có browser client key, operation, key, request fingerprint và response
  và response reference; unique constraint ở database.
- [x] Áp idempotency + transaction + PRG cho bán hàng, điều chỉnh kho, hủy sale, tạo product,
  upload ảnh và tạo backup.
- [x] Có endpoint tra trạng thái idempotency để xử lý trường hợp request đã commit nhưng
  client mất response; không tự queue hoặc tự replay offline.

#### PWA, cache và lỗi mạng

- [x] Bổ sung PWA icon, manifest shortcut Bán hàng/Sản phẩm/Tồn kho và `display=standalone`.
- [x] Service worker chỉ cache asset tĩnh; không cache HTML động, API,
  giá vốn/lợi nhuận, POST, sale hay inventory response.
- [ ] Hiển thị trạng thái mất kết nối và thông báo thay đổi chưa được xác nhận; chỉ toast
  thành công sau commit.
- [x] Test route/layout mobile, CSRF/session/cost-lock regression; browser mới không tự mở khóa giá vốn.
- [x] Viết `docs/MOBILE_PWA.md` về mobile/PWA và giới hạn không có offline write.

Điều kiện hoàn thành: toàn bộ nghiệp vụ hằng ngày dùng được ở viewport 360 px, không cuộn
ngang toàn trang, double-submit không tạo bản ghi trùng, xung đột nhiều thiết bị không ghi
đè âm thầm và dữ liệu nhạy cảm không đi vào cache.

### Kết quả Phase 8 — 2026-07-31

- PWA có manifest/icon/shortcut local và worker chỉ cache GET dưới `/static/`; worker xóa cache
  cũ, không cache HTML động, media, dữ liệu giá vốn hoặc thao tác ghi.
- Product, inventory và lịch sử/chi tiết sale có card mobile; desktop giữ bảng. Off-canvas và
  bottom navigation không che nội dung nhờ padding mobile.
- Upload ảnh gợi ý camera sau, preview cục bộ; server decode/verify JPEG/PNG/WebP, giới hạn
  10 MB/30 MP, xử lý EXIF/thumbnail; media LAN kiểm tra lại nội dung trước khi trả MIME.
- `IdempotencyRecord` có unique constraint `(client_key, operation, key)`, fingerprint payload và URL
  kết quả. Sale, điều chỉnh tồn, hủy sale, tạo product và backup chống gửi trùng; test thread
  xác minh hai submit cùng key chỉ commit một lần. Có lệnh `purge_idempotency --days 30`.
- Category/product/variant và timeout security dùng revision compare-and-save atomically; stale
  edit bị từ chối tiếng Việt thay vì ghi đè. Transaction tồn kho và sale vẫn là authoritative.
- Middleware không đánh dấu backup là ordinary write, tránh backup tự chờ active marker của
  chính request; đây là regression test cho deadlock vừa phát hiện.
- Gate WSL: formatter, Ruff, mypy, Django check, migration check và 95 pytest pass.
- Không có Chrome/Chromium hoặc runner E2E trong WSL và `AGENTS.md` không cho thêm Node toolchain;
  viewport/touch/camera thật và Add to Home Screen được để `REQUIRES USER DEVICE VALIDATION`
  trong Phase 13, không được coi là chứng nhận thiết bị thật.

### Phase 9 — Windows Service, launcher và truy cập thiết bị

#### Waitress và WinSW

- [x] Cấu hình Waitress một process, 4 threads, listen mặc định `0.0.0.0:2505`; launcher,
  installer và health dùng chung nguồn port.
- [ ] Benchmark số thread và SQLite lock contention trên máy host.
- [x] Cấu hình WinSW tên hiển thị `Shop Hoà Thuận Server`, automatic delayed start,
  graceful stop, working directory, environment và log path trong ProgramData.
- [x] Cấu hình restart hữu hạn/backoff; sau ngưỡng lỗi WinSW dừng restart loop.
- [x] Kiểm thử start trước khi có browser truy cập, kill PID/recovery, stop/start lại và không tạo
  server thứ hai trên test service.
- [ ] Kiểm thử reboot/autostart và shutdown Windows thật.

#### Launcher và chẩn đoán

- [x] Tạo `ShopHoaThuanLauncher.exe` dạng GUI, không console và không chứa server thứ hai.
- [x] Launcher kiểm tra `127.0.0.1:2505/health/`, yêu cầu SCM start service nếu cần, poll
  hữu hạn rồi mở browser/PWA.
- [x] Khi lỗi hiển thị `SHOP-SERVER-001` cùng thông tin mở thư mục nhật ký.
- [x] Chống nhiều launcher đồng thời và không bao giờ spawn thêm Waitress; đã có regression test.
- [x] Tạo health-check utility dùng chung cho launcher, installer/updater và native smoke.

#### LAN, firewall và trang thiết bị

- [x] Có installer/test helper tạo Windows Firewall inbound rule cho TCP `2505` ở profile
  Private/Public, giới hạn `LocalSubnet`; mDNS chưa được tự động mở.
- [x] Installer/launcher và trang thiết bị ghi rõ ứng dụng dùng trực tiếp trong LAN: không tạo
  account, không quảng bá Internet, PIN chỉ bảo vệ giá vốn và firewall chỉ cho `LocalSubnet`.
- [x] Chạy helper bằng Administrator; service, health, recovery và firewall LAN trên Private/Public đã PASS trên
  test data, service/rule được cleanup.
- [ ] Quảng bá hostname `shophoathuan.local` bằng mDNS trong LAN từ cùng server/service,
  không tạo thêm server ghi database và không phụ thuộc DNS Internet.
- [ ] Phát hiện/xử lý trùng tên mDNS; trang thiết bị phải hiển thị tên thực tế đang được
  quảng bá thay vì báo thành công giả.
- [x] Trang `/settings/device-access/` hiển thị hostname, health, LAN IPv4,
  `http://<IP-LAN>:2505`, QR và Tailscale hostname nếu được cấu hình.
- [ ] Ưu tiên và kiểm thử hostname cố định `http://shophoathuan.local:2505` qua mDNS.
- [ ] Thêm khu vực **Mạng của máy chủ** trên `/settings/device-access/`, hiển thị trong LAN,
  gồm loại kết nối, trạng thái, tên Wi-Fi (SSID) của máy Windows host
  và nút **Làm mới thông tin mạng**.
- [ ] Đọc SSID phía server bằng Windows Native Wi-Fi API hoặc cơ chế hệ thống ổn định
  tương đương và phải hoạt động khi Django chạy dưới Windows Service; không yêu cầu người
  dùng mở terminal, chạy `ipconfig` hoặc `netsh`.
- [ ] Hiển thị đúng các trạng thái:
  - `Đang kết nối Wi-Fi: <Tên Wi-Fi>`;
  - `Máy chủ đang kết nối bằng mạng dây`;
  - `Máy chủ chưa kết nối mạng`;
  - `Không thể xác định mạng đang sử dụng`.
- [ ] Nếu có nhiều network adapter, ưu tiên adapter đang kết nối và có đường mạng hoạt động.
  Không trả credential, khóa bảo mật, BSSID, MAC hoặc cấu hình mạng nhạy cảm; không dùng SSID
  để xác thực/phân quyền và không ghi SSID vào log nếu không cần thiết.
- [ ] Không hiển thị loopback/APIPA/adapter không hoạt động; không yêu cầu `ipconfig`.
- [ ] Tài liệu hóa DHCP reservation, DNS router `home.arpa` tùy chọn và Tailscale; không
  port-forward/public tunnel hoặc đăng ký DNS công cộng tự động.
- [ ] Test phân giải `.local` trên Windows, Android và iOS; test fallback IP, Tailscale,
  đổi IP, trùng hostname, profile Public và firewall removal khi uninstall.
- [ ] Test thông tin mạng host khi dùng Wi-Fi, đổi SSID, dùng Ethernet, mất mạng, có nhiều
  adapter, service không đủ quyền đọc và SSID chứa tiếng Việt/khoảng trắng/ký tự đặc biệt.

Điều kiện hoàn thành: reboot Windows tự có đúng một server instance; double-click shortcut
mở ứng dụng mà không có terminal; điện thoại truy cập được bằng
`shophoathuan.local:2505` hoặc fallback IP trên LAN; lỗi startup có thông báo/log
đủ chẩn đoán.

### Phase 10 — Đóng gói runtime và bộ cài Windows

#### Build và artifact

- [x] Dùng `uv.lock` và project-local Windows environment trong pipeline build.
- [ ] Chứng nhận build reproducible trên Windows 10/11 x64 sạch.
- [x] PyInstaller `onedir` đóng gói Python, Django, Waitress, templates/static/migrations và
  local assets; artifact không phụ thuộc Python/uv/Git/Node trên host.
- [x] Tạo GUI executable cho launcher, backup, restore, updater và utility migration/health.
- [x] Đóng gói WinSW, version metadata và checksum artifact; license/SBOM release đầy đủ còn thiếu.
- [ ] Smoke test tương tác mọi executable trong thư mục staging trước khi tạo installer.

#### Inno Setup và thiết lập PIN

- [x] Tạo `ShopHoaThuan-Setup-<version>.exe`, compile trên Windows x64 và kiểm tra version/
  checksum artifact.
- [x] Cấu hình copy app vào Program Files; chỉ tạo thư mục ProgramData còn thiếu, không ghi đè
  database/media/config.
- [x] Cấu hình sinh secret an toàn, chạy migration runner riêng, collect/static verify và hướng
  dẫn thiết lập PIN.
- [x] Không tạo account hoặc mật khẩu trong installer/repair; chỉ hướng dẫn thiết lập PIN khi
  installation chưa có PIN.
- [x] Đã có flow đăng ký/start WinSW, tạo firewall LAN-scoped cho Private/Public, health check, Desktop/Start Menu
  shortcut và URL khởi động; việc chạy thật cần Administrator.
- [ ] Xác minh flow installer/service/firewall/health trên Windows sạch.
- [ ] Nếu lỗi: dừng/gỡ service mới, rollback application files/rule/shortcut, giữ data,
  ghi log và hiển thị mã lỗi tiếng Việt.
- [x] Uninstaller không khai báo xóa ProgramData mặc định.
- [ ] Bổ sung và kiểm thử xác nhận hai lần trước khi xóa data tùy chọn.
- [ ] Repair/reinstall/update cùng version không làm mất dữ liệu hoặc tạo lại PIN.

#### Chứng nhận cài đặt

- [ ] Test trên Windows sạch không Python, uv, Git, Node, SQLite, PostgreSQL hay Docker.
- [ ] Test install, cancel, failure injection, reinstall, repair, uninstall giữ data,
  uninstall xóa data có xác nhận, reboot và launcher.
- [x] Ghi lại phiên bản Windows, checksum installer và kết quả native smoke trong release evidence.

Điều kiện hoàn thành: bộ cài duy nhất tạo được hệ thống chạy sau reboot trên Windows sạch,
không terminal, dữ liệu sống ngoài Program Files và mọi đường lỗi cài đặt đã thử đều giữ
được dữ liệu cũ.

### Phase 11 — Backup và restore

#### Snapshot và manifest

- [x] Dùng SQLite backup API trong operation lock; không copy trực tiếp database đang ghi.
- [x] Snapshot database và media vào staging cùng filesystem, đóng gói ZIP bằng atomic rename.
- [x] Manifest chứa app version, schema version, UTC time, timezone, SHA-256 database,
  checksum media, category/product/variant/sale counts và tổng tồn.
- [x] Chạy integrity check trên snapshot, mở database read-only, kiểm tra checksum/archive
  traversal và chỉ sau đó báo thành công.
- [x] Cleanup staging lỗi; backup lỗi không xuất hiện như archive hợp lệ.

#### Backup GUI và retention

- [x] Tạo `ShopHoaThuanBackup.exe` và shortcut; hỗ trợ Sao lưu ngay bằng GUI.
- [x] Chống double-submit bằng idempotency/operation lock.
- [ ] Scheduler nhẹ tạo backup tự động và cảnh báo backup quá hạn.
- [x] Hàm retention giữ 7 daily, 4 weekly, 12 monthly và không xóa bản pinned đã có test.
- [x] Chỉ hướng dẫn sync/copy ZIP đã hoàn chỉnh ra USB/NAS/cloud, không sync live database.

#### Restore GUI và rollback

- [x] Tạo `ShopHoaThuanRestore.exe` chỉ dùng trên host: đọc manifest, checksum, schema và
  yêu cầu xác nhận mạnh.
- [x] Trước restore tạo/xác minh backup hiện tại; bật maintenance, drain transaction và
  snapshot data hiện tại để rollback.
- [ ] Dừng service native/start health trong restore trên Windows thật.
- [x] Restore database/media qua staging + atomic directory/file swap và integrity check.
- [ ] Chạy migration nếu cần, service start, health và smoke test trên installer/service thật.
- [x] Nếu lỗi, backend khôi phục cả database và media trước restore và giữ rollback evidence.
- [ ] Xác minh rollback bằng restore độc lập, thiếu dung lượng, mất quyền và chuyển máy.
- [x] Viết `docs/BACKUP_AND_RESTORE.md` và `docs/MIGRATION_TO_NEW_DEVICE.md` bằng tiếng Việt,
  không yêu cầu người dùng chạy command line.

Điều kiện hoàn thành: backup đang chạy cùng server là snapshot nhất quán; restore thử vào
máy/thư mục sạch khôi phục đúng database và media; failure injection quay lại được dữ liệu
trước restore.

### Phase 12 — Update, migration và rollback

#### Gói update và preflight

- [x] Tạo `ShopHoaThuan-Update-<version>.exe` GUI cho update file cục bộ.
- [x] Xác minh Semantic Version, checksum, version hiện tại, target version và chặn downgrade
  hoặc cài lại cùng version ngoài chủ ý.
- [ ] Bổ sung chữ ký số, kiểm tra kiến trúc và disk-space preflight cho release package.
- [ ] Hiển thị changelog và tiến trình tiếng Việt; chi tiết kỹ thuật chỉ trong log.
- [x] Dùng một operation lock để không chạy đồng thời update/restore/backup và không nhận
  sale/inventory mới khi vào maintenance.

#### Quy trình an toàn

- [x] Preflight database/schema; maintenance; drain transaction; tạo và xác minh pre-update
  backup trong transaction update.
- [x] Dừng service, lưu app cũ vào `rollback\app-<version>`, stage app mới và thay toàn bộ
  application tree để không còn file cũ sót lại.
- [x] Chạy migration runner có exit code/log và kiểm tra health sau khi start; deployment check
  được chạy trong Windows build pipeline.
- [ ] Chạy đầy đủ `check --deploy`, collect/static và business smoke sau update trên native service.
- [x] Chỉ thoát maintenance và xóa staging sau khi transaction kết thúc; exception path cleanup
  đã có test.
- [x] Giữ nguyên ProgramData data/media/backups/logs/config/PIN/sales/inventory khi thay app tree.

#### Migration và rollback

- [ ] Áp dụng expand-and-contract; migration destructive chỉ ở release sau khi code/data
  chuyển đổi đã được xác minh.
- [ ] Phân loại migration rollback-safe và migration cần restore pre-update backup cho release
  1.1.0 → 1.2.0 thực tế.
- [x] Nếu migration/service/health lỗi: dừng app mới, phục hồi app cũ và database nếu cần,
  start app cũ và giải phóng maintenance; đã có WSL exception-path test.
- [ ] Không để trạng thái nửa cũ/nửa mới; lưu journal từng bước để lần chạy sau biết tiếp
  tục hay rollback.
- [x] Test validation, staging failure, complete-tree replacement, migration failure cleanup và
  maintenance release trong WSL.
- [ ] Test update hai version, chạy updater hai lần, health/service failure và process kill trên
  native Windows service.
- [x] Viết `docs/UPDATE.md` và `docs/RELEASE_PROCESS.md`.

Điều kiện hoàn thành: update giữ nguyên toàn bộ dữ liệu; mọi lỗi được chủ động tiêm trong
test đều hoặc hoàn tất an toàn hoặc rollback về phiên bản cũ hoạt động; không còn trạng thái
maintenance/staging mồ côi.

### Phase 13 — Kiểm thử và chứng nhận release

#### Evidence và tài liệu

- [x] Tạo `docs/REQUIREMENT_TRACEABILITY_MATRIX.md` ánh xạ requirement → implementation → test
  → evidence → limitation.
- [x] Tạo `docs/FINAL_ACCEPTANCE_REPORT.md`, `docs/KNOWN_LIMITATIONS.md` và
  `docs/RELEASE_CHECKLIST.md`.
- [x] Tạo `docs/USER_DEVICE_VALIDATION.md` cho các bước cần Windows sạch, reboot, LAN phone,
  camera và PWA thật; không chuyển phần code/test tự động sang người dùng.
- [x] Cập nhật `artifacts/acceptance/README.md` và ghi artifact/checksum không chứa dữ liệu thật.

#### Ma trận release bắt buộc

- [ ] Cài mới/reinstall/repair/uninstall trên Windows 10 và 11 x64 sạch; xác nhận không cần
  Python, uv, Git, Node, SQLite riêng hay terminal.
- [ ] Service auto-start sau reboot, chạy khi chưa có browser truy cập, launcher/PWA không tạo server
  trùng và đóng browser không dừng service.
- [ ] Chạy E2E desktop và các viewport mobile: mở ứng dụng, product + camera image + multi-size,
  cost unlock/edit, inventory, sale, report, cancel và backup.
- [ ] Test hai thiết bị sửa đồng thời, hai sale tranh tồn kho, double-submit, request timeout
  sau commit, CSRF lỗi, session hết hạn và mất mạng.
- [ ] Xác minh response/cache/log/CSV/hóa đơn không lộ giá vốn khi khóa.
- [ ] Backup live rồi restore sang máy/thư mục sạch; so sánh counts, tổng tồn, sale gần nhất,
  doanh thu, ảnh và PIN.
- [ ] Update qua ít nhất hai version, migration lỗi, health lỗi, rollback code/database và
  chạy lại updater.
- [ ] Mô phỏng mất điện/process termination tại checkpoint quan trọng trong giới hạn lab;
  kiểm tra journal/staging/rollback tự phục hồi hoặc đưa ra hướng dẫn rõ ràng.

#### Hiệu năng, bảo mật và vận hành

- [ ] Benchmark startup, dashboard, product list, sale commit, report và backup trên máy
  cấu hình tương đương host; ghi ngưỡng chấp nhận và RAM ổn định khi soak test.
- [ ] Audit query count/N+1, pagination, thumbnail/lazy loading, Waitress threads và SQLite
  lock contention.
- [ ] Audit biên truy cập LAN trực tiếp, CSRF, session cookie, PIN rate limit, upload, path
  traversal, backup ZIP, host header, log redaction, firewall và secret/config ACL.
- [ ] Kiểm tra disk-full, database corrupt, media thiếu, clock/timezone, DST không áp dụng
  tại Việt Nam và thời điểm sát 0 giờ.
- [ ] Hoàn thiện `docs/TROUBLESHOOTING.md`, ảnh/mô tả trực quan và bảng mã lỗi.
- [ ] Tạo release checklist, SBOM/dependency inventory, checksum, changelog và archive
  evidence kiểm thử.

Điều kiện phát hành: tất cả P0/P1 đã đóng; formatter/lint/mypy/test/check đạt; cài đặt
Windows sạch, mobile edit, backup→restore, update giữ dữ liệu và rollback về trạng thái chạy
được đều có bằng chứng. Nếu thiếu một trong năm nhóm chứng nhận này, Phase 13 và bản phát
hành vẫn là **chưa hoàn thành**.

## Nhật ký kiểm tra

### Phase 1 — 2026-07-31

- Python: 3.12.13; Django: 5.2.16 LTS.
- `ruff format --check`: đạt.
- `ruff check`: đạt.
- `mypy --strict`: đạt, 45 source files.
- `manage.py check`: đạt, không có issue.
- `makemigrations --check --dry-run`: không có thay đổi model chưa migration.
- `pytest`: 21 test đạt.
- Waitress smoke test: khởi động production entry point, migrate/seed và `/health/` đạt.
- Static assets Bootstrap/HTMX/Chart.js được phục vụ local.
- `check --deploy` còn cảnh báo HTTPS/secure cookie có chủ đích vì bản local LAN chạy HTTP;
  rủi ro và hướng Tailscale/HTTPS đã được ghi nhận cho Phase 6.
- Restore từ giao diện và kiểm thử bộ cài Windows sạch vẫn thuộc Phase 6.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 1.

### Phase 2 — 2026-07-31

- `ruff format --check` và `ruff check`: đạt.
- `mypy --strict`: đạt, 50 source files.
- Django system/migration checks: đạt.
- `pytest`: 29 test đạt.
- Waitress smoke test: đạt sau migration mới.
- Ảnh test và database development tạm đã được dọn khỏi workspace.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 2.

### Phase 3 — 2026-07-31

- `ruff format --check`, `ruff check`, `mypy --strict`: đạt.
- Django system/migration checks: đạt.
- `pytest`: 38 test đạt.
- Waitress smoke test: đạt.
- Không sử dụng `localStorage`; phiên mở khóa chỉ nằm trong Django session.
- Backup chứa database chỉ tạo/tải được khi giá vốn đã mở khóa.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 3.

### Phase 4 — 2026-07-31

- `ruff format --check`: đạt, 60 file đã đúng định dạng.
- `ruff check`: đạt.
- `mypy --strict`: đạt, 56 source files.
- Django system/migration checks: đạt, không có model chưa migration.
- `pytest`: 54 test đạt, gồm validation tổng tiền/dòng bán và transaction cạnh tranh SQLite.
- Waitress smoke test: đạt.
- Browser smoke test: mở ứng dụng LAN, thêm size M, sửa giá thực tế, cảnh báo dưới giá niêm yết,
  giảm giá, hoàn tất giao dịch, xem chi tiết và hóa đơn đều đạt; console không có lỗi.
- Response tìm sản phẩm khi khóa không chứa `cost_price`; hóa đơn không chứa giá vốn hoặc
  lợi nhuận.
- Database/media thử nghiệm trình duyệt trong `/tmp` đã được xóa sau kiểm tra.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 4.

### Phase 5 — 2026-07-31

- `ruff format --check`, `ruff check`, `mypy --strict`: đạt.
- Django system/migration checks: đạt.
- `pytest`: 64 test đạt, gồm báo cáo, dashboard, CSV và bảo vệ giá vốn.
- Dashboard hiển thị doanh thu theo ngày/tháng, giao dịch gần đây, sản phẩm/size bán chạy,
  doanh thu theo loại/phương thức thanh toán và cảnh báo tồn.
- Báo cáo chỉ dùng giao dịch hoàn thành, tính ngày theo `Asia/Ho_Chi_Minh`, phân bổ giảm giá
  chính xác; khi khóa không truy vấn/render giá vốn.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 5.

### Phase 6 — 2026-07-31

- Smoke test HTTP: tạo PIN, loại/sản phẩm/size/tồn, hoàn tất bán, báo cáo và hủy/hoàn tồn.
- Audit mã nguồn và test xác nhận CSRF Django, session HTTP-only, PIN hash/rate-limit,
  response không lộ giá vốn khi khóa và các thao tác tồn/bán chạy trong transaction nguyên tử.
- `docs/OPERATIONS.md` ghi rõ quy tắc tồn kho, snapshot, giá vốn và báo cáo.

Không còn lỗi quan trọng đã xác nhận trong phạm vi Phase 6.
