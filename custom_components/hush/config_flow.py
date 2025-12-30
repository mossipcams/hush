"""Config flow for Hush integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .const import (
    CONF_CATEGORY_BEHAVIORS,
    CONF_DELIVERY_TARGET,
    CONF_QUIET_HOURS_ENABLED,
    CONF_QUIET_HOURS_END,
    CONF_QUIET_HOURS_START,
    DEFAULT_QUIET_HOURS_ENABLED,
    DEFAULT_QUIET_HOURS_END,
    DEFAULT_QUIET_HOURS_START,
    DOMAIN,
    Category,
    CategoryBehavior,
    DEFAULT_CATEGORY_BEHAVIORS,
)


def get_notify_services(hass: HomeAssistant) -> list[str]:
    """Get available notification services."""
    services: list[str] = []
    notify_domain = hass.services.async_services().get("notify", {})

    for service_name in notify_domain:
        # Skip our own service and persistent_notification
        if service_name not in ("hush", "persistent_notification"):
            services.append(f"notify.{service_name}")

    return sorted(services)


class HushConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Hush."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        # Only allow one instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        errors: dict[str, str] = {}

        notify_services = get_notify_services(self.hass)

        if not notify_services:
            return self.async_abort(reason="no_notify_services")

        if user_input is not None:
            return self.async_create_entry(
                title="Hush",
                data={
                    CONF_DELIVERY_TARGET: user_input[CONF_DELIVERY_TARGET],
                },
                options={
                    CONF_QUIET_HOURS_ENABLED: DEFAULT_QUIET_HOURS_ENABLED,
                    CONF_QUIET_HOURS_START: DEFAULT_QUIET_HOURS_START,
                    CONF_QUIET_HOURS_END: DEFAULT_QUIET_HOURS_END,
                    CONF_CATEGORY_BEHAVIORS: {},
                },
            )

        # Build service options
        service_options = [
            selector.SelectOptionDict(value=svc, label=svc.replace("notify.", "").replace("_", " ").title())
            for svc in notify_services
        ]

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DELIVERY_TARGET): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=service_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> HushOptionsFlow:
        """Get the options flow for this handler."""
        return HushOptionsFlow()


class HushOptionsFlow(OptionsFlow):
    """Handle Hush options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage basic options."""
        if user_input is not None:
            # Check if user wants advanced settings
            if user_input.pop("show_advanced", False):
                self._pending_options = user_input
                return await self.async_step_advanced()

            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    **user_input,
                },
            )

        notify_services = get_notify_services(self.hass)
        current_target = self.config_entry.data.get(CONF_DELIVERY_TARGET, "")

        # Ensure current target is in list
        if current_target and current_target not in notify_services:
            notify_services.insert(0, current_target)

        service_options = [
            selector.SelectOptionDict(value=svc, label=svc.replace("notify.", "").replace("_", " ").title())
            for svc in notify_services
        ]

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_DELIVERY_TARGET,
                        default=current_target,
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(
                            options=service_options,
                            mode=selector.SelectSelectorMode.DROPDOWN,
                        )
                    ),
                    vol.Required(
                        CONF_QUIET_HOURS_ENABLED,
                        default=self.config_entry.options.get(
                            CONF_QUIET_HOURS_ENABLED, DEFAULT_QUIET_HOURS_ENABLED
                        ),
                    ): selector.BooleanSelector(),
                    vol.Required(
                        CONF_QUIET_HOURS_START,
                        default=self.config_entry.options.get(
                            CONF_QUIET_HOURS_START, DEFAULT_QUIET_HOURS_START
                        ),
                    ): selector.TimeSelector(),
                    vol.Required(
                        CONF_QUIET_HOURS_END,
                        default=self.config_entry.options.get(
                            CONF_QUIET_HOURS_END, DEFAULT_QUIET_HOURS_END
                        ),
                    ): selector.TimeSelector(),
                    vol.Optional("show_advanced", default=False): selector.BooleanSelector(),
                }
            ),
        )

    async def async_step_advanced(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage advanced category options."""
        if user_input is not None:
            # Merge pending options with category behaviors
            category_behaviors = {
                Category.SAFETY: user_input.get("safety_behavior", DEFAULT_CATEGORY_BEHAVIORS[Category.SAFETY]),
                Category.SECURITY: user_input.get("security_behavior", DEFAULT_CATEGORY_BEHAVIORS[Category.SECURITY]),
                Category.DEVICE: user_input.get("device_behavior", DEFAULT_CATEGORY_BEHAVIORS[Category.DEVICE]),
                Category.MOTION: user_input.get("motion_behavior", DEFAULT_CATEGORY_BEHAVIORS[Category.MOTION]),
                Category.INFO: user_input.get("info_behavior", DEFAULT_CATEGORY_BEHAVIORS[Category.INFO]),
            }

            return self.async_create_entry(
                title="",
                data={
                    **self.config_entry.options,
                    **getattr(self, "_pending_options", {}),
                    CONF_CATEGORY_BEHAVIORS: category_behaviors,
                },
            )

        current_behaviors = self.config_entry.options.get(CONF_CATEGORY_BEHAVIORS, {})

        behavior_options = [
            selector.SelectOptionDict(value=b.value, label=b.value.replace("_", " ").title())
            for b in CategoryBehavior
        ]

        return self.async_show_form(
            step_id="advanced",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "safety_behavior",
                        default=current_behaviors.get(
                            Category.SAFETY, DEFAULT_CATEGORY_BEHAVIORS[Category.SAFETY]
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=behavior_options)
                    ),
                    vol.Required(
                        "security_behavior",
                        default=current_behaviors.get(
                            Category.SECURITY, DEFAULT_CATEGORY_BEHAVIORS[Category.SECURITY]
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=behavior_options)
                    ),
                    vol.Required(
                        "device_behavior",
                        default=current_behaviors.get(
                            Category.DEVICE, DEFAULT_CATEGORY_BEHAVIORS[Category.DEVICE]
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=behavior_options)
                    ),
                    vol.Required(
                        "motion_behavior",
                        default=current_behaviors.get(
                            Category.MOTION, DEFAULT_CATEGORY_BEHAVIORS[Category.MOTION]
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=behavior_options)
                    ),
                    vol.Required(
                        "info_behavior",
                        default=current_behaviors.get(
                            Category.INFO, DEFAULT_CATEGORY_BEHAVIORS[Category.INFO]
                        ),
                    ): selector.SelectSelector(
                        selector.SelectSelectorConfig(options=behavior_options)
                    ),
                }
            ),
        )
