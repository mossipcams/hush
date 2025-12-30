"""Tests for the Hush integration setup and service."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.core import HomeAssistant, ServiceCall

from custom_components.hush import (
    _async_register_panel,
    _async_register_websocket_api,
    _is_quiet_hours,
    _should_deliver,
    async_reload_entry,
    async_setup,
    async_setup_entry,
    async_unload_entry,
    ws_get_config,
    ws_get_notifications,
    ws_save_config,
)
from custom_components.hush.const import (
    CONF_CATEGORY_BEHAVIORS,
    CONF_DELIVERY_TARGET,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DOMAIN,
    Category,
    CategoryBehavior,
)
from custom_components.hush.storage import NotificationStore


@pytest.fixture
def mock_hass() -> MagicMock:
    """Create a mock Home Assistant instance."""
    hass = MagicMock(spec=HomeAssistant)
    hass.data = {}
    hass.config = MagicMock()
    hass.config.path = MagicMock(return_value="/tmp/hass_test")
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
    hass.http = MagicMock()
    hass.http.register_static_path = MagicMock()
    hass.components = MagicMock()
    hass.components.frontend = MagicMock()
    hass.components.frontend.async_register_built_in_panel = MagicMock()
    hass.config_entries = MagicMock()
    return hass


@pytest.fixture
def mock_config_entry() -> MagicMock:
    """Create a mock config entry."""
    entry = MagicMock()
    entry.entry_id = "test_entry_id"
    entry.domain = DOMAIN
    entry.title = "Hush"
    entry.data = {
        CONF_DELIVERY_TARGET: "notify.mobile_app_test",
    }
    entry.options = {
        CONF_QUIET_HOURS_ENABLED: True,
        CONF_QUIET_HOURS_START: "22:00",
        CONF_QUIET_HOURS_END: "07:00",
        CONF_CATEGORY_BEHAVIORS: {},
    }
    entry.unique_id = DOMAIN
    entry.async_on_unload = MagicMock()
    entry.add_update_listener = MagicMock()
    return entry


class TestAsyncSetup:
    """Tests for async_setup."""

    @pytest.mark.asyncio
    async def test_async_setup_initializes_domain_data(self, mock_hass: MagicMock) -> None:
        """Test that async_setup initializes hass.data[DOMAIN]."""
        result = await async_setup(mock_hass, {})
        assert result is True
        assert DOMAIN in mock_hass.data


class TestIsQuietHours:
    """Tests for _is_quiet_hours function.

    Note: These tests verify the quiet hours logic directly in test_quiet_hours.py
    using a reference implementation. Here we test the actual function integration.
    """

    def test_quiet_hours_uses_config_values(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that _is_quiet_hours uses config entry values."""
        mock_config_entry.options[CONF_QUIET_HOURS_START] = "22:00"
        mock_config_entry.options[CONF_QUIET_HOURS_END] = "07:00"

        # Just verify it runs without error - actual time logic tested in test_quiet_hours.py
        result = _is_quiet_hours(mock_hass, mock_config_entry)
        assert isinstance(result, bool)

    def test_quiet_hours_handles_same_day_window(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test same-day quiet hours window."""
        mock_config_entry.options[CONF_QUIET_HOURS_START] = "14:00"
        mock_config_entry.options[CONF_QUIET_HOURS_END] = "16:00"

        result = _is_quiet_hours(mock_hass, mock_config_entry)
        assert isinstance(result, bool)


class TestShouldDeliver:
    """Tests for _should_deliver function."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock notification store."""
        store = MagicMock(spec=NotificationStore)
        store.async_is_duplicate = AsyncMock(return_value=False)
        return store

    @pytest.mark.asyncio
    async def test_always_notify_delivers(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that ALWAYS_NOTIFY behavior always delivers."""
        mock_hass.data[DOMAIN] = {"store": mock_store}

        result = await _should_deliver(
            mock_hass,
            mock_config_entry,
            Category.SAFETY,
            CategoryBehavior.ALWAYS_NOTIFY,
            "Test message",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_log_only_never_delivers(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that LOG_ONLY behavior never delivers."""
        mock_hass.data[DOMAIN] = {"store": mock_store}

        result = await _should_deliver(
            mock_hass,
            mock_config_entry,
            Category.MOTION,
            CategoryBehavior.LOG_ONLY,
            "Test message",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_respect_quiet_during_quiet_hours(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that NOTIFY_RESPECT_QUIET doesn't deliver during quiet hours."""
        mock_hass.data[DOMAIN] = {"store": mock_store}
        mock_config_entry.options[CONF_QUIET_HOURS_ENABLED] = True

        with patch("custom_components.hush._is_quiet_hours", return_value=True):
            result = await _should_deliver(
                mock_hass,
                mock_config_entry,
                Category.SECURITY,
                CategoryBehavior.NOTIFY_RESPECT_QUIET,
                "Test message",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_notify_respect_quiet_outside_quiet_hours(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that NOTIFY_RESPECT_QUIET delivers outside quiet hours."""
        mock_hass.data[DOMAIN] = {"store": mock_store}
        mock_config_entry.options[CONF_QUIET_HOURS_ENABLED] = True

        with patch("custom_components.hush._is_quiet_hours", return_value=False):
            result = await _should_deliver(
                mock_hass,
                mock_config_entry,
                Category.SECURITY,
                CategoryBehavior.NOTIFY_RESPECT_QUIET,
                "Test message",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_notify_with_dedup_blocks_duplicate(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that NOTIFY_WITH_DEDUP blocks duplicate messages."""
        mock_store.async_is_duplicate = AsyncMock(return_value=True)
        mock_hass.data[DOMAIN] = {"store": mock_store}
        mock_config_entry.options[CONF_QUIET_HOURS_ENABLED] = False

        result = await _should_deliver(
            mock_hass,
            mock_config_entry,
            Category.INFO,
            CategoryBehavior.NOTIFY_WITH_DEDUP,
            "Test message",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_notify_once_per_hour_uses_60min_window(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that NOTIFY_ONCE_PER_HOUR uses 60-minute dedup window."""
        mock_hass.data[DOMAIN] = {"store": mock_store}
        mock_config_entry.options[CONF_QUIET_HOURS_ENABLED] = False

        await _should_deliver(
            mock_hass,
            mock_config_entry,
            Category.DEVICE,
            CategoryBehavior.NOTIFY_ONCE_PER_HOUR,
            "Test message",
        )

        # Verify it was called with 60 minute window
        mock_store.async_is_duplicate.assert_called_once_with("Test message", 60)

    @pytest.mark.asyncio
    async def test_quiet_hours_disabled_delivers(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that delivery works when quiet hours are disabled."""
        mock_hass.data[DOMAIN] = {"store": mock_store}
        mock_config_entry.options[CONF_QUIET_HOURS_ENABLED] = False

        result = await _should_deliver(
            mock_hass,
            mock_config_entry,
            Category.SECURITY,
            CategoryBehavior.NOTIFY_RESPECT_QUIET,
            "Test message",
        )
        assert result is True


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    @pytest.mark.asyncio
    async def test_unload_removes_service(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that unload removes the notify service."""
        mock_store = MagicMock()
        mock_store.async_close = AsyncMock()
        mock_hass.data[DOMAIN] = {"store": mock_store, "entry": mock_config_entry}

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_hass.services.async_remove.assert_called_once_with(DOMAIN, "notify")
        mock_store.async_close.assert_called_once()
        assert DOMAIN not in mock_hass.data

    @pytest.mark.asyncio
    async def test_unload_handles_missing_store(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that unload handles missing store gracefully."""
        mock_hass.data[DOMAIN] = {}

        result = await async_unload_entry(mock_hass, mock_config_entry)

        assert result is True


class TestAsyncReloadEntry:
    """Tests for async_reload_entry."""

    @pytest.mark.asyncio
    async def test_reload_calls_unload_and_setup(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock
    ) -> None:
        """Test that reload calls unload and then setup."""
        with patch(
            "custom_components.hush.async_unload_entry", new_callable=AsyncMock
        ) as mock_unload:
            with patch(
                "custom_components.hush.async_setup_entry", new_callable=AsyncMock
            ) as mock_setup:
                await async_reload_entry(mock_hass, mock_config_entry)

                mock_unload.assert_called_once_with(mock_hass, mock_config_entry)
                mock_setup.assert_called_once_with(mock_hass, mock_config_entry)


class TestAsyncRegisterPanel:
    """Tests for _async_register_panel."""

    @pytest.mark.asyncio
    async def test_register_panel_skips_when_no_js(self, mock_hass: MagicMock) -> None:
        """Test that panel registration is skipped when JS file doesn't exist."""
        # Create a temp directory structure that doesn't have the panel JS
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # The function uses Path(__file__).parent / "hush-panel.js"
            # So we patch Path to return a path that doesn't exist
            fake_init_path = Path(tmpdir) / "__init__.py"
            fake_init_path.touch()

            with patch("custom_components.hush.Path") as mock_path:
                mock_file_path = MagicMock()
                mock_file_path.parent = Path(tmpdir)
                mock_path.return_value = mock_file_path

                await _async_register_panel(mock_hass)

                # Should not register panel when JS doesn't exist
                mock_hass.components.frontend.async_register_built_in_panel.assert_not_called()

    @pytest.mark.asyncio
    async def test_register_panel_registers_when_js_exists(self, mock_hass: MagicMock) -> None:
        """Test that panel is registered when JS file exists."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create fake JS files
            panel_path = Path(tmpdir) / "hush-panel.js"
            panel_path.touch()
            card_path = Path(tmpdir) / "hush-history-card.js"
            card_path.touch()

            with patch("custom_components.hush.Path") as mock_path:
                mock_file_path = MagicMock()
                mock_file_path.parent = Path(tmpdir)
                mock_path.return_value = mock_file_path

                await _async_register_panel(mock_hass)

                mock_hass.http.register_static_path.assert_called()
                mock_hass.components.frontend.async_register_built_in_panel.assert_called_once()


class TestAsyncRegisterWebsocketApi:
    """Tests for _async_register_websocket_api."""

    @pytest.mark.asyncio
    async def test_registers_websocket_commands(self, mock_hass: MagicMock) -> None:
        """Test that WebSocket commands are registered."""
        with patch("custom_components.hush.websocket_api") as mock_ws_api:
            await _async_register_websocket_api(mock_hass)

            # Should register 3 commands
            assert mock_ws_api.async_register_command.call_count == 3


class TestWsGetNotifications:
    """Tests for ws_get_notifications WebSocket handler."""

    @pytest.fixture
    def mock_connection(self) -> MagicMock:
        """Create a mock WebSocket connection."""
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        return conn

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock notification store."""
        store = MagicMock()
        store.async_get_recent = AsyncMock(return_value=[])
        store.async_get_today_stats = AsyncMock(
            return_value={
                "total": 5,
                "safety_count": 1,
                "delivered_count": 3,
            }
        )
        return store

    @pytest.mark.asyncio
    async def test_get_notifications_returns_data(
        self, mock_hass: MagicMock, mock_connection: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that get_notifications returns notifications and stats."""
        mock_hass.data[DOMAIN] = {"store": mock_store}
        msg = {"id": 1, "type": "hush/get_notifications", "limit": 10}

        # The ws handler is decorated - get the underlying function
        handler = ws_get_notifications.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_connection.send_result.assert_called_once()
        call_args = mock_connection.send_result.call_args
        assert call_args[0][0] == 1
        assert "notifications" in call_args[0][1]
        assert "stats" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_notifications_error_when_not_configured(
        self, mock_hass: MagicMock, mock_connection: MagicMock
    ) -> None:
        """Test that get_notifications sends error when not configured."""
        mock_hass.data = {}
        msg = {"id": 1, "type": "hush/get_notifications"}

        handler = ws_get_notifications.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once_with(
            1, "not_configured", "Hush is not configured"
        )


class TestWsGetConfig:
    """Tests for ws_get_config WebSocket handler."""

    @pytest.fixture
    def mock_connection(self) -> MagicMock:
        """Create a mock WebSocket connection."""
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        return conn

    @pytest.mark.asyncio
    async def test_get_config_returns_config(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_connection: MagicMock
    ) -> None:
        """Test that get_config returns configuration."""
        mock_hass.data[DOMAIN] = {"entry": mock_config_entry}
        msg = {"id": 1, "type": "hush/get_config"}

        handler = ws_get_config.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_connection.send_result.assert_called_once()
        call_args = mock_connection.send_result.call_args
        assert call_args[0][0] == 1
        result = call_args[0][1]
        assert "config" in result
        assert "notify_services" in result
        assert result["config"]["delivery_target"] == "notify.mobile_app_test"

    @pytest.mark.asyncio
    async def test_get_config_error_when_not_configured(
        self, mock_hass: MagicMock, mock_connection: MagicMock
    ) -> None:
        """Test that get_config sends error when not configured."""
        mock_hass.data = {}
        msg = {"id": 1, "type": "hush/get_config"}

        handler = ws_get_config.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once_with(
            1, "not_configured", "Hush is not configured"
        )


class TestWsSaveConfig:
    """Tests for ws_save_config WebSocket handler."""

    @pytest.fixture
    def mock_connection(self) -> MagicMock:
        """Create a mock WebSocket connection."""
        conn = MagicMock()
        conn.send_result = MagicMock()
        conn.send_error = MagicMock()
        return conn

    @pytest.mark.asyncio
    async def test_save_config_updates_entry(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_connection: MagicMock
    ) -> None:
        """Test that save_config updates the config entry."""
        mock_hass.data[DOMAIN] = {"entry": mock_config_entry}
        msg = {
            "id": 1,
            "type": "hush/save_config",
            "config": {
                "delivery_target": "notify.new_target",
                "quiet_hours_enabled": False,
                "quiet_hours_start": "23:00",
                "quiet_hours_end": "06:00",
                "category_behaviors": {"safety": "always_notify"},
            },
        }

        handler = ws_save_config.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_hass.config_entries.async_update_entry.assert_called_once()
        mock_connection.send_result.assert_called_once_with(1, {"success": True})

    @pytest.mark.asyncio
    async def test_save_config_error_when_not_configured(
        self, mock_hass: MagicMock, mock_connection: MagicMock
    ) -> None:
        """Test that save_config sends error when not configured."""
        mock_hass.data = {}
        msg = {"id": 1, "type": "hush/save_config", "config": {}}

        handler = ws_save_config.__wrapped__
        await handler(mock_hass, mock_connection, msg)

        mock_connection.send_error.assert_called_once_with(
            1, "not_configured", "Hush is not configured"
        )


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    @pytest.fixture
    def mock_store(self) -> MagicMock:
        """Create a mock notification store."""
        store = MagicMock()
        store.async_initialize = AsyncMock()
        store.async_add_notification = AsyncMock()
        store.async_is_duplicate = AsyncMock(return_value=False)
        return store

    @pytest.mark.asyncio
    async def test_setup_entry_initializes_store(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that setup_entry initializes the storage."""
        with patch("custom_components.hush.NotificationStore", return_value=mock_store):
            with patch(
                "custom_components.hush._async_register_websocket_api", new_callable=AsyncMock
            ):
                with patch("custom_components.hush._async_register_panel", new_callable=AsyncMock):
                    result = await async_setup_entry(mock_hass, mock_config_entry)

        assert result is True
        mock_store.async_initialize.assert_called_once()
        mock_hass.services.async_register.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_service_handler(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that the notify service handler works correctly."""
        service_handler = None

        def capture_handler(domain, service, handler, schema):
            nonlocal service_handler
            service_handler = handler

        mock_hass.services.async_register = MagicMock(side_effect=capture_handler)

        with patch("custom_components.hush.NotificationStore", return_value=mock_store):
            with patch(
                "custom_components.hush._async_register_websocket_api", new_callable=AsyncMock
            ):
                with patch("custom_components.hush._async_register_panel", new_callable=AsyncMock):
                    await async_setup_entry(mock_hass, mock_config_entry)

        # Create a mock service call
        mock_call = MagicMock(spec=ServiceCall)
        mock_call.data = {
            "message": "Test notification",
            "title": "Test Title",
            "data": {"category": "safety"},
        }
        mock_call.context = MagicMock()
        mock_call.context.parent_id = None

        # Call the service handler
        await service_handler(mock_call)

        # Verify notification was stored
        mock_store.async_add_notification.assert_called_once()
        # Verify delivery was attempted (safety always notifies)
        mock_hass.services.async_call.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_service_handler_entity_classification(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that service handler classifies entities correctly."""
        service_handler = None

        def capture_handler(domain, service, handler, schema):
            nonlocal service_handler
            service_handler = handler

        mock_hass.services.async_register = MagicMock(side_effect=capture_handler)

        with patch("custom_components.hush.NotificationStore", return_value=mock_store):
            with patch(
                "custom_components.hush._async_register_websocket_api", new_callable=AsyncMock
            ):
                with patch("custom_components.hush._async_register_panel", new_callable=AsyncMock):
                    await async_setup_entry(mock_hass, mock_config_entry)

        # Create a mock service call with entity_id
        mock_call = MagicMock(spec=ServiceCall)
        mock_call.data = {
            "message": "Motion detected",
            "data": {"entity_id": "binary_sensor.motion_detector"},
        }
        mock_call.context = MagicMock()
        mock_call.context.parent_id = None

        # Call the service handler
        await service_handler(mock_call)

        # Verify notification was stored
        mock_store.async_add_notification.assert_called_once()

    @pytest.mark.asyncio
    async def test_setup_entry_service_handler_no_delivery_log_only(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that LOG_ONLY notifications are not delivered."""
        service_handler = None

        def capture_handler(domain, service, handler, schema):
            nonlocal service_handler
            service_handler = handler

        mock_hass.services.async_register = MagicMock(side_effect=capture_handler)
        mock_config_entry.options[CONF_CATEGORY_BEHAVIORS] = {
            Category.INFO: CategoryBehavior.LOG_ONLY.value,
        }

        with patch("custom_components.hush.NotificationStore", return_value=mock_store):
            with patch(
                "custom_components.hush._async_register_websocket_api", new_callable=AsyncMock
            ):
                with patch("custom_components.hush._async_register_panel", new_callable=AsyncMock):
                    await async_setup_entry(mock_hass, mock_config_entry)

        mock_call = MagicMock(spec=ServiceCall)
        mock_call.data = {
            "message": "Info message",
            "data": {"category": "info"},
        }
        mock_call.context = MagicMock()
        mock_call.context.parent_id = None

        await service_handler(mock_call)

        # Notification should be stored
        mock_store.async_add_notification.assert_called_once()
        # But not delivered
        mock_hass.services.async_call.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_entry_service_handler_with_extra_data(
        self, mock_hass: MagicMock, mock_config_entry: MagicMock, mock_store: MagicMock
    ) -> None:
        """Test that extra data is passed through to delivery."""
        service_handler = None

        def capture_handler(domain, service, handler, schema):
            nonlocal service_handler
            service_handler = handler

        mock_hass.services.async_register = MagicMock(side_effect=capture_handler)

        with patch("custom_components.hush.NotificationStore", return_value=mock_store):
            with patch(
                "custom_components.hush._async_register_websocket_api", new_callable=AsyncMock
            ):
                with patch("custom_components.hush._async_register_panel", new_callable=AsyncMock):
                    await async_setup_entry(mock_hass, mock_config_entry)

        mock_call = MagicMock(spec=ServiceCall)
        mock_call.data = {
            "message": "Safety alert",
            "title": "Alert",
            "data": {
                "category": "safety",
                "actions": [{"action": "OPEN", "title": "Open"}],
            },
        }
        mock_call.context = MagicMock()
        mock_call.context.parent_id = None

        await service_handler(mock_call)

        # Verify extra data was passed through
        call_args = mock_hass.services.async_call.call_args
        assert "data" in call_args[0][2]
        assert "actions" in call_args[0][2]["data"]
