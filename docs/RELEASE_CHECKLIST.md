# Release checklist

## WSL gate

- [x] Ruff format check
- [x] Ruff check
- [x] mypy
- [x] Django system checks
- [x] migration consistency
- [x] full pytest

## Windows build gate

- [x] Python Windows project-local, PyInstaller and Inno Setup identified
- [x] server/migration/health/launcher/update/backup/restore artifacts built
- [x] native server health smoke
- [x] native migration runner
- [x] installer artifact and SHA-256
- [x] native server `/health/` smoke on isolated test data
- [x] Administrator service/firewall/recovery trên test data
- [ ] Production/clean Windows service ACL, reboot/autostart
- [ ] clean Windows install/reinstall/uninstall

## Data safety gate

- [x] backup uses SQLite backup API and checksum/integrity validation
- [x] restore stages and keeps pre-restore backup
- [x] update validates package and cleans staging on exception
- [ ] restore on independent Windows test machine
- [ ] update success/failure/rollback with native service

## Release decision

Chỉ chọn `ACCEPTED FOR PRODUCTION RELEASE` khi toàn bộ ô bắt buộc đã có evidence. Trạng thái
hiện tại là `CONDITIONALLY ACCEPTED` cho internal build validation, chưa phải nghiệm thu
production cuối.
