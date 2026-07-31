from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.core.models import ShopSecuritySettings
from apps.core.operations import maintenance_state
from shop_hoa_thuan.runner import run_first_setup, run_migrations, schema_is_compatible
from shop_hoa_thuan.runtime import RuntimePaths


def test_runner_module_can_load_before_django_setup() -> None:
    """Packaged server imports runner before calling django.setup()."""
    result = subprocess.run(
        [sys.executable, "-c", "import shop_hoa_thuan.runner"],
        capture_output=True,
        check=False,
        text=True,
    )

    assert result.returncode == 0, result.stderr


@pytest.mark.django_db
def test_schema_runner_reports_current_test_schema_as_compatible() -> None:
    assert schema_is_compatible() is True


@pytest.mark.django_db
def test_migration_runner_releases_maintenance_after_failure(tmp_path: Path) -> None:
    with (
        override_settings(RUNTIME_PATHS=RuntimePaths(tmp_path)),
        patch("shop_hoa_thuan.runner.call_command", side_effect=RuntimeError("migration failed")),
    ):
        with pytest.raises(RuntimeError, match="migration failed"):
            run_migrations()
        assert maintenance_state() is None


@pytest.mark.django_db
def test_first_run_only_executes_once_without_overwriting_existing_data(tmp_path: Path) -> None:
    with override_settings(RUNTIME_PATHS=RuntimePaths(tmp_path)):
        run_first_setup(username="chushop", password="MatKhau-Rieng-2026!", pin="2468")
        owner = get_user_model().objects.get(username="chushop")
        assert owner.is_superuser is True
        assert ShopSecuritySettings.objects.get(pk=1).cost_price_pin_hash != "2468"
        with pytest.raises(RuntimeError, match="đã được thiết lập"):
            run_first_setup(username="other", password="MatKhau-Rieng-2026!", pin="1357")
        assert get_user_model().objects.count() == 1
