# Requirement traceability matrix

| Nhóm yêu cầu | Implementation | Test/evidence | Status | Limitation |
|---|---|---|---|---|
| Một server ghi một data directory | `apps/core/operations.py`, `server.py` | process lease test, native server smoke | PASS trong WSL/native smoke | WinSW/SCM thật cần UAC |
| Maintenance và drain write | `maintenance_operation`, middleware, backup/restore/update | operations, backup, runner, update tests | PASS nền tảng | failure injection trên service thật chưa chạy |
| Service không migrate | `server.py`, WinSW XML, migration runner | runner tests, XML regression, native migration | PASS | SCM thật chưa chạy |
| Production config/host | `runtime.py`, `settings.py`, build script | Django system/deploy checks | PASS với 4 warning HTTP có chủ đích | HTTPS/Tailscale thật chưa chứng nhận |
| Version duy nhất | `pyproject.toml`, `version.py`, frozen specs | version/manifest/health tests | PASS | artifact release signing chưa có |
| Logging rotation/redaction | `settings.py`, `logging.py` | logging tests, PyInstaller spec | PASS | soak log growth trên host thật chưa chạy |
| Health | `apps/core/views.py`, `health_check.py` | healthy/maintenance/schema/db unavailable tests | PASS | service recovery thật cần UAC |
| Private media | media view/service | private media/path/content tests | PASS | camera thật chưa kiểm thử |
| Mobile/PWA/idempotency | templates, static worker, services | pytest mobile/idempotency/concurrency | PASS tự động trong WSL | viewport/camera/A2HS thật chưa có |
| Backup/restore | `apps/core/backup.py`, backup/restore GUI | snapshot, checksum, integrity, restore tests | PASS nền tảng | restore qua installer/service thật chưa chạy |
| Update/rollback | `apps/core/update.py`, `update_runner.py`, package builder | validation, tree replacement, maintenance tests | PASS nền tảng | Windows SCM failure injection chưa chạy |
| Installer/service/LAN | Inno/WinSW/scripts | Windows build + native server smoke | BLOCKED | cần Administrator, reboot, LAN device |
| Final acceptance | `docs/FINAL_ACCEPTANCE_REPORT.md` | gate ledger/evidence | BLOCKED | chưa phải release production |
