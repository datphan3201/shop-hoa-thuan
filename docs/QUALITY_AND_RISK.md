# Chất lượng, bảo mật và rủi ro phát hành

## Quality gates

| Gate | Mục tiêu | Trạng thái hiện tại |
|---|---|---|
| Formatter/Ruff/mypy | Style, lỗi tĩnh, type contract | PASS ở gate WSL gần nhất trước thay đổi docs; phải chạy lại trước commit phase. |
| Django check/migration check | Settings/schema sạch | PASS ở gate WSL gần nhất; phải chạy lại trước commit phase. |
| Pytest | Nghiệp vụ, lock, maintenance, health, media, idempotency | 104 PASS ở WSL sau regression frozen startup; không thay thế gate phase cuối. |
| Native Windows smoke | Artifact không cần Python dev | `ShopHoaThuanServer.exe` PASS `/health/` với Windows test data. |
| SCM/firewall | Service, recovery, Private LAN/cleanup | Chưa chạy: cần UAC. |
| Clean machine/device | Reboot, LAN phone, camera/PWA, installer | Chưa chạy: Phase 13. |

Chỉ report PASS khi lệnh đã chạy trên commit tương ứng.

## Threat model

| Tài sản | Nguy cơ | Kiểm soát hiện có | Evidence còn cần |
|---|---|---|---|
| Giá vốn/PIN | Lộ response, cache, CSV, log | Cost lock server, PIN hash/rate-limit, redaction, PWA static-only cache | Device/browser cache Phase 13. |
| Sale/tồn | Double submit, race, partial commit | Atomic service, DB constraints, idempotency, movement audit | Multi-device LAN Phase 13. |
| Runtime data | Hai server ghi DB, maintenance stuck | OS lease, write drain timeout/finally, stale tests | Windows SCM/crash/reboot. |
| Upload/media | Fake image, traversal, public file | Pillow decode/verify, limits, authenticated media root | Camera/browser thật. |
| Network | Public exposure/host header/firewall | No port-forward, no wildcard host, Private firewall plan | LAN firewall inspection. |
| Backup/update | Snapshot/restore/update mất data | Maintenance + SQLite backup foundation | End-to-end Phase 11–12. |

## Django deployment warnings

| Warning | Phân loại | Cách xử lý |
|---|---|---|
| `security.W004`, `W008`, `W012`, `W016` khi `SHOP_USE_HTTPS=false` | Chấp nhận có điều kiện HTTP LAN tin cậy | Không bật redirect/HSTS/secure cookie khi server thực sự là HTTP; không dùng mạng công cộng. |
| `security.W005`, `W021` khi HTTPS/Tailscale | Chấp nhận có điều kiện | Không HSTS include-subdomain/preload nếu không kiểm soát HTTPS cho mọi subdomain. |
| `security.W009` | Phải sửa nếu production gặp | Runtime production dùng secret random dài; secret test ngắn không hợp lệ. |
| `ALLOWED_HOSTS=*` | Không chấp nhận | Runtime reject wildcard; chỉ host/IP hợp lệ. |

## Rủi ro còn lại

| Mức | Rủi ro | Điều kiện đóng |
|---|---|---|
| High | Chưa restore backup thật | Phase 11 restore DB/media/count/checksum và rollback failure PASS. |
| High | Chưa update/rollback | Phase 12 1.0.0→1.1.0 và failure injection PASS. |
| High | Installer/service chưa clean Windows/reboot | Phase 9–10 + Phase 13 evidence. |
| High | Mobile camera/PWA/LAN chưa thiết bị thật | Phase 13 device validation PASS. |
| Medium | HTTP LAN không mã hóa transport | Chỉ LAN tin cậy; HTTPS/Tailscale theo cấu hình, không public Internet. |
| Medium | SQLite trên cloud/network filesystem | Chỉ giữ DB local. |
| Medium | Chưa benchmark 5k variants/20k sale items | Phase 13 performance dataset. |

## Quy tắc phản ứng sự cố

1. Không xóa database/media/log trước khi xác định data directory và tạo backup.
2. Health schema incompatible: không restart loop; dùng migration runner qua installer/updater.
3. Maintenance timeout: không kill write transaction; để operation exit và đọc log.
4. Restore/update lỗi: giữ evidence/staging, xác minh rollback/health trước cleanup.
5. Không đưa secret, database, backup hay log shop lên Git/chat công khai.
