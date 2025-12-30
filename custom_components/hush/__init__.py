"""Hush - Smart Notifications for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.helpers import config_validation as cv

from .classifier import classify_entity
from .const import (
    ATTR_CATEGORY,
    ATTR_DATA,
    ATTR_ENTITY_ID,
    ATTR_MESSAGE,
    ATTR_TITLE,
    CONF_CATEGORY_BEHAVIORS,
    CONF_DELIVERY_TARGET,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DEFAULT_CATEGORY_BEHAVIORS,
    DEFAULT_QUIET_HOURS_ENABLED,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DOMAIN,
    SERVICE_NOTIFY,
    Category,
    CategoryBehavior,
)
from .storage import NotificationStore

if TYPE_CHECKING:
    from homeassistant.helpers.typing import ConfigType

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = []

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): cv.string,
        vol.Optional(ATTR_TITLE): cv.string,
        vol.Optional(ATTR_DATA): vol.Schema(
            {
                vol.Optional(ATTR_CATEGORY): vol.In([c.value for c in Category]),
                vol.Optional(ATTR_ENTITY_ID): cv.string,
            },
            extra=vol.ALLOW_EXTRA,
        ),
    }
)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Hush component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Hush from a config entry."""
    # Initialize storage
    storage_path = Path(hass.config.path(".storage")) / DOMAIN
    store = NotificationStore(hass, storage_path)
    await store.async_initialize()

    # Store runtime data
    hass.data[DOMAIN] = {
        "store": store,
        "entry": entry,
    }

    # Register the notification service
    async def async_handle_notify(call: ServiceCall) -> None:
        """Handle the notify service call."""
        message = call.data[ATTR_MESSAGE]
        title = call.data.get(ATTR_TITLE)
        data = call.data.get(ATTR_DATA, {})

        # Get entity_id from data or try to extract from context
        entity_id = data.get(ATTR_ENTITY_ID)
        if not entity_id and call.context.parent_id:
            # Try to get from automation context (best effort)
            pass

        # Determine category
        category_str = data.get(ATTR_CATEGORY)
        if category_str:
            category = Category(category_str)
        elif entity_id:
            category = classify_entity(entity_id)
        else:
            category = Category.INFO

        # Get behavior for category
        category_behaviors = entry.options.get(CONF_CATEGORY_BEHAVIORS, {})
        behavior = CategoryBehavior(
            category_behaviors.get(category, DEFAULT_CATEGORY_BEHAVIORS[category])
        )

        # Check if we should deliver
        should_deliver = await _should_deliver(hass, entry, category, behavior, message)

        # Store notification
        await store.async_add_notification(
            message=message,
            title=title,
            category=category,
            entity_id=entity_id,
            delivered=should_deliver,
        )

        # Deliver if needed
        if should_deliver:
            delivery_target = entry.data.get(CONF_DELIVERY_TARGET)
            if delivery_target:
                domain, service = delivery_target.split(".", 1)
                service_data = {"message": message}
                if title:
                    service_data["title"] = title
                # Pass through extra data (for mobile app features like actions)
                extra_data = {k: v for k, v in data.items() if k not in (ATTR_CATEGORY, ATTR_ENTITY_ID)}
                if extra_data:
                    service_data["data"] = extra_data

                await hass.services.async_call(domain, service, service_data)

        _LOGGER.debug(
            "Processed notification: message=%s, category=%s, delivered=%s",
            message[:50],
            category,
            should_deliver,
        )

    hass.services.async_register(
        DOMAIN, SERVICE_NOTIFY, async_handle_notify, schema=SERVICE_SCHEMA
    )

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    # Register WebSocket API
    await _async_register_websocket_api(hass)

    # Register panel
    await _async_register_panel(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Remove service
    hass.services.async_remove(DOMAIN, SERVICE_NOTIFY)

    # Close storage
    if DOMAIN in hass.data:
        store = hass.data[DOMAIN].get("store")
        if store:
            await store.async_close()
        hass.data.pop(DOMAIN)

    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def _should_deliver(
    hass: HomeAssistant,
    entry: ConfigEntry,
    category: Category,
    behavior: CategoryBehavior,
    message: str,
) -> bool:
    """Determine if a notification should be delivered."""
    # Safety always delivers
    if behavior == CategoryBehavior.ALWAYS_NOTIFY:
        return True

    # Log only never delivers
    if behavior == CategoryBehavior.LOG_ONLY:
        return False

    # Check quiet hours for applicable behaviors
    if behavior in (CategoryBehavior.NOTIFY_RESPECT_QUIET, CategoryBehavior.NOTIFY_WITH_DEDUP):
        quiet_enabled = entry.options.get(CONF_QUIET_HOURS_ENABLED, DEFAULT_QUIET_HOURS_ENABLED)
        if quiet_enabled and _is_quiet_hours(hass, entry):
            return False

    # Check deduplication for applicable behaviors
    if behavior in (CategoryBehavior.NOTIFY_WITH_DEDUP, CategoryBehavior.NOTIFY_ONCE_PER_HOUR):
        store: NotificationStore = hass.data[DOMAIN]["store"]
        window_minutes = 60 if behavior == CategoryBehavior.NOTIFY_ONCE_PER_HOUR else 5
        if await store.async_is_duplicate(message, window_minutes):
            return False

    return True


def _is_quiet_hours(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Check if current time is within quiet hours."""
    import datetime

    now = datetime.datetime.now(tz=datetime.UTC).astimezone()
    current_time = now.time()

    start_str = entry.options.get(CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START)
    end_str = entry.options.get(CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END)

    start = datetime.time.fromisoformat(start_str)
    end = datetime.time.fromisoformat(end_str)

    # Handle overnight quiet hours (e.g., 22:00 - 07:00)
    if start > end:
        return current_time >= start or current_time < end
    else:
        return start <= current_time < end


async def _async_register_panel(hass: HomeAssistant) -> None:
    """Register the Hush settings panel."""
    # Check if panel JS exists
    panel_path = Path(__file__).parent / "hush-panel.js"
    if not panel_path.exists():
        _LOGGER.warning("Panel JS not found at %s, skipping panel registration", panel_path)
        return

    hass.http.register_static_path(
        "/hush/hush-panel.js",
        str(panel_path),
        cache_headers=False,
    )

    # Also register the card JS
    card_path = Path(__file__).parent / "hush-history-card.js"
    if card_path.exists():
        hass.http.register_static_path(
            "/hush/hush-history-card.js",
            str(card_path),
            cache_headers=False,
        )
        # Register card as a frontend resource
        hass.components.frontend.async_register_frontend_url_path(
            "/hush/hush-history-card.js"
        )

    hass.components.frontend.async_register_built_in_panel(
        component_name="custom",
        sidebar_title="Hush",
        sidebar_icon="mdi:bell-sleep",
        frontend_url_path="hush",
        config={
            "_panel_custom": {
                "name": "hush-settings-panel",
                "module_url": "/hush/hush-panel.js",
            }
        },
        require_admin=False,
    )


async def _async_register_websocket_api(hass: HomeAssistant) -> None:
    """Register WebSocket API handlers."""
    websocket_api.async_register_command(hass, ws_get_notifications)
    websocket_api.async_register_command(hass, ws_get_config)
    websocket_api.async_register_command(hass, ws_save_config)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hush/get_notifications",
        vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=100)),
    }
)
@websocket_api.async_response
async def ws_get_notifications(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Handle get_notifications WebSocket command."""
    if DOMAIN not in hass.data:
        connection.send_error(msg["id"], "not_configured", "Hush is not configured")
        return

    store: NotificationStore = hass.data[DOMAIN]["store"]
    limit = msg.get("limit", 50)

    notifications = await store.async_get_recent(limit)
    stats = await store.async_get_today_stats()

    connection.send_result(
        msg["id"],
        {
            "notifications": [n.to_dict() for n in notifications],
            "stats": stats,
        },
    )


@websocket_api.websocket_command({vol.Required("type"): "hush/get_config"})
@websocket_api.async_response
async def ws_get_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Handle get_config WebSocket command."""
    if DOMAIN not in hass.data:
        connection.send_error(msg["id"], "not_configured", "Hush is not configured")
        return

    entry: ConfigEntry = hass.data[DOMAIN]["entry"]

    # Get available notify services
    notify_services = []
    notify_domain = hass.services.async_services().get("notify", {})
    for service_name in notify_domain:
        if service_name not in ("hush", "persistent_notification"):
            notify_services.append({
                "service": f"notify.{service_name}",
                "name": service_name.replace("_", " ").title(),
            })

    config = {
        "delivery_target": entry.data.get(CONF_DELIVERY_TARGET, ""),
        "quiet_hours_enabled": entry.options.get(CONF_QUIET_HOURS_ENABLED, DEFAULT_QUIET_HOURS_ENABLED),
        "quiet_hours_start": entry.options.get(CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START),
        "quiet_hours_end": entry.options.get(CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END),
        "category_behaviors": entry.options.get(CONF_CATEGORY_BEHAVIORS, {}),
    }

    connection.send_result(
        msg["id"],
        {
            "config": config,
            "notify_services": sorted(notify_services, key=lambda x: x["name"]),
        },
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "hush/save_config",
        vol.Required("config"): dict,
    }
)
@websocket_api.async_response
async def ws_save_config(
    hass: HomeAssistant,
    connection: websocket_api.ActiveConnection,
    msg: dict,
) -> None:
    """Handle save_config WebSocket command."""
    if DOMAIN not in hass.data:
        connection.send_error(msg["id"], "not_configured", "Hush is not configured")
        return

    entry: ConfigEntry = hass.data[DOMAIN]["entry"]
    new_config = msg["config"]

    # Update config entry data (delivery_target)
    new_data = {**entry.data}
    if "delivery_target" in new_config:
        new_data[CONF_DELIVERY_TARGET] = new_config["delivery_target"]

    # Update options
    new_options = {**entry.options}
    if "quiet_hours_enabled" in new_config:
        new_options[CONF_QUIET_HOURS_ENABLED] = new_config["quiet_hours_enabled"]
    if "quiet_hours_start" in new_config:
        new_options[CONF_QUIET_HOURS_START] = new_config["quiet_hours_start"]
    if "quiet_hours_end" in new_config:
        new_options[CONF_QUIET_HOURS_END] = new_config["quiet_hours_end"]
    if "category_behaviors" in new_config:
        new_options[CONF_CATEGORY_BEHAVIORS] = new_config["category_behaviors"]

    hass.config_entries.async_update_entry(entry, data=new_data, options=new_options)

    connection.send_result(msg["id"], {"success": True})
