"""Tests for the Hush config flow."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from homeassistant.config_entries import SOURCE_USER
from homeassistant.data_entry_flow import FlowResultType

from custom_components.hush.config_flow import HushConfigFlow, HushOptionsFlow, get_notify_services
from custom_components.hush.const import (
    CONF_CATEGORY_BEHAVIORS,
    CONF_DELIVERY_TARGET,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DOMAIN,
    Category,
    CategoryBehavior,
)


class TestHushConfigFlow:
    """Tests for HushConfigFlow."""

    @pytest.fixture
    def mock_hass_with_notify(self) -> MagicMock:
        """Create a mock hass with notify services."""
        hass = MagicMock()
        hass.services.async_services.return_value = {
            "notify": {
                "mobile_app_phone": {},
                "mobile_app_tablet": {},
                "persistent_notification": {},
            }
        }
        return hass

    @pytest.fixture
    def mock_hass_no_notify(self) -> MagicMock:
        """Create a mock hass without notify services."""
        hass = MagicMock()
        hass.services.async_services.return_value = {
            "notify": {
                "persistent_notification": {},
            }
        }
        return hass

    @pytest.mark.asyncio
    async def test_flow_user_step_shows_form(self, mock_hass_with_notify: MagicMock) -> None:
        """Test that user step shows form."""
        flow = HushConfigFlow()
        flow.hass = mock_hass_with_notify

        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                result = await flow.async_step_user()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "user"

    @pytest.mark.asyncio
    async def test_flow_user_step_creates_entry(self, mock_hass_with_notify: MagicMock) -> None:
        """Test that user step creates entry with valid input."""
        flow = HushConfigFlow()
        flow.hass = mock_hass_with_notify

        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_create_entry") as mock_create:
                    mock_create.return_value = {"type": FlowResultType.CREATE_ENTRY}

                    result = await flow.async_step_user({
                        CONF_DELIVERY_TARGET: "notify.mobile_app_phone",
                    })

                    assert result["type"] == FlowResultType.CREATE_ENTRY
                    mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_flow_aborts_no_notify_services(self, mock_hass_no_notify: MagicMock) -> None:
        """Test that flow aborts when no notify services available."""
        flow = HushConfigFlow()
        flow.hass = mock_hass_no_notify

        with patch.object(flow, "async_set_unique_id", return_value=None):
            with patch.object(flow, "_abort_if_unique_id_configured"):
                with patch.object(flow, "async_abort") as mock_abort:
                    mock_abort.return_value = {"type": FlowResultType.ABORT}

                    result = await flow.async_step_user()

                    mock_abort.assert_called_once_with(reason="no_notify_services")

    @pytest.mark.asyncio
    async def test_flow_excludes_hush_service(self, mock_hass_with_notify: MagicMock) -> None:
        """Test that flow excludes the hush notify service from options."""
        mock_hass_with_notify.services.async_services.return_value = {
            "notify": {
                "hush": {},  # Our own service
                "mobile_app_phone": {},
                "persistent_notification": {},
            }
        }

        flow = HushConfigFlow()
        flow.hass = mock_hass_with_notify

        # Verify get_notify_services excludes hush
        services = get_notify_services(mock_hass_with_notify)

        assert "notify.hush" not in services
        assert "notify.persistent_notification" not in services
        assert "notify.mobile_app_phone" in services


class TestGetNotifyServices:
    """Tests for get_notify_services function."""

    def test_returns_sorted_services(self) -> None:
        """Test that services are returned sorted."""
        hass = MagicMock()
        hass.services.async_services.return_value = {
            "notify": {
                "zeta_phone": {},
                "alpha_phone": {},
                "mobile_app_beta": {},
            }
        }

        services = get_notify_services(hass)

        assert services == [
            "notify.alpha_phone",
            "notify.mobile_app_beta",
            "notify.zeta_phone",
        ]

    def test_handles_empty_notify_domain(self) -> None:
        """Test handling when notify domain has no services."""
        hass = MagicMock()
        hass.services.async_services.return_value = {}

        services = get_notify_services(hass)

        assert services == []


class TestHushOptionsFlow:
    """Tests for HushOptionsFlow."""

    @pytest.fixture
    def mock_config_entry(self) -> MagicMock:
        """Create a mock config entry for options flow."""
        entry = MagicMock()
        entry.entry_id = "test_entry_id"
        entry.domain = DOMAIN
        entry.data = {CONF_DELIVERY_TARGET: "notify.mobile_app_test"}
        entry.options = {
            CONF_QUIET_HOURS_ENABLED: True,
            CONF_QUIET_HOURS_START: DEFAULT_QUIET_HOURS_START,
            CONF_QUIET_HOURS_END: DEFAULT_QUIET_HOURS_END,
            CONF_CATEGORY_BEHAVIORS: {},
        }
        return entry

    @pytest.fixture
    def mock_hass(self) -> MagicMock:
        """Create mock hass for options flow."""
        hass = MagicMock()
        hass.services.async_services.return_value = {
            "notify": {
                "mobile_app_test": {},
                "mobile_app_other": {},
            }
        }
        return hass

    @pytest.mark.asyncio
    async def test_options_flow_init_shows_form(
        self, mock_config_entry: MagicMock, mock_hass: MagicMock
    ) -> None:
        """Test that options flow init step shows form."""
        flow = HushOptionsFlow()
        flow.hass = mock_hass

        with patch.object(type(flow), "config_entry", new=mock_config_entry):
            result = await flow.async_step_init()

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "init"

    @pytest.mark.asyncio
    async def test_options_flow_saves_basic_options(
        self, mock_config_entry: MagicMock, mock_hass: MagicMock
    ) -> None:
        """Test that options flow saves basic options."""
        flow = HushOptionsFlow()
        flow.hass = mock_hass

        with patch.object(type(flow), "config_entry", new=mock_config_entry):
            with patch.object(flow, "async_create_entry") as mock_create:
                mock_create.return_value = {"type": FlowResultType.CREATE_ENTRY}

                result = await flow.async_step_init({
                    CONF_DELIVERY_TARGET: "notify.mobile_app_other",
                    CONF_QUIET_HOURS_ENABLED: False,
                    CONF_QUIET_HOURS_START: "23:00",
                    CONF_QUIET_HOURS_END: "06:00",
                })

                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_options_flow_advanced_step(
        self, mock_config_entry: MagicMock, mock_hass: MagicMock
    ) -> None:
        """Test that show_advanced triggers advanced step."""
        flow = HushOptionsFlow()
        flow.hass = mock_hass

        with patch.object(type(flow), "config_entry", new=mock_config_entry):
            result = await flow.async_step_init({
                CONF_DELIVERY_TARGET: "notify.mobile_app_test",
                CONF_QUIET_HOURS_ENABLED: True,
                CONF_QUIET_HOURS_START: "22:00",
                CONF_QUIET_HOURS_END: "07:00",
                "show_advanced": True,
            })

        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "advanced"

    @pytest.mark.asyncio
    async def test_options_flow_advanced_saves_behaviors(
        self, mock_config_entry: MagicMock, mock_hass: MagicMock
    ) -> None:
        """Test that advanced step saves category behaviors."""
        flow = HushOptionsFlow()
        flow.hass = mock_hass
        flow._pending_options = {
            CONF_DELIVERY_TARGET: "notify.mobile_app_test",
            CONF_QUIET_HOURS_ENABLED: True,
        }

        with patch.object(type(flow), "config_entry", new=mock_config_entry):
            with patch.object(flow, "async_create_entry") as mock_create:
                mock_create.return_value = {"type": FlowResultType.CREATE_ENTRY}

                result = await flow.async_step_advanced({
                    "safety_behavior": CategoryBehavior.ALWAYS_NOTIFY,
                    "security_behavior": CategoryBehavior.NOTIFY_RESPECT_QUIET,
                    "device_behavior": CategoryBehavior.NOTIFY_ONCE_PER_HOUR,
                    "motion_behavior": CategoryBehavior.LOG_ONLY,
                    "info_behavior": CategoryBehavior.NOTIFY_WITH_DEDUP,
                })

                mock_create.assert_called_once()
                call_args = mock_create.call_args
                assert CONF_CATEGORY_BEHAVIORS in call_args.kwargs["data"]
