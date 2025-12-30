"""Fixtures for Hush tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.hush.const import (
    CONF_CATEGORY_BEHAVIORS,
    CONF_DELIVERY_TARGET,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DOMAIN,
)


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Create a mock config entry."""
    entry = MagicMock(spec=ConfigEntry)
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.title = "Hush"
    entry.data = {
        CONF_DELIVERY_TARGET: "notify.mobile_app_test",
    }
    entry.options = {
        CONF_QUIET_HOURS_ENABLED: True,
        CONF_QUIET_HOURS_START: DEFAULT_QUIET_HOURS_START,
        CONF_QUIET_HOURS_END: DEFAULT_QUIET_HOURS_END,
        CONF_CATEGORY_BEHAVIORS: {},
    }
    entry.unique_id = DOMAIN
    return entry


@pytest.fixture
def mock_hass() -> HomeAssistant:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/hass")
    hass.services = MagicMock()
    hass.services.async_services = MagicMock(
        return_value={
            "notify": {
                "mobile_app_test": {},
                "persistent_notification": {},
            }
        }
    )
    hass.services.async_call = AsyncMock()
    hass.services.async_register = MagicMock()
    hass.services.async_remove = MagicMock()
    return hass


@pytest.fixture
def tmp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage path."""
    storage_path = tmp_path / ".storage" / DOMAIN
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path
