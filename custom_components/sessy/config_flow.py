"""Config flow for Sessy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_HOST,
    CONF_NAME,
    CONF_SCAN_INTERVAL
)
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from sessypy.devices import get_sessy_device, SessyBattery, SessyP1Meter, SessyCTMeter
from sessypy.util import SessyConnectionException, SessyLoginException

from .const import DEFAULT_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_POWER, DOMAIN

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""

    try:
        device = await get_sessy_device(
            host = data.get(CONF_HOST),
            username = data.get(CONF_USERNAME),
            password = data.get(CONF_PASSWORD),
        )
    except SessyLoginException:
        raise InvalidAuth
    except SessyConnectionException:
        raise CannotConnect
    
    if device is None:
        raise CannotConnect
    
    device_id = device.serial_number[0:4]
    # Return info that you want to store in the config entry.
    if isinstance(device, SessyBattery):
        return {"title": f"Sessy Battery {device_id}"}
    elif isinstance(device, SessyP1Meter):
        return {"title": "Sessy P1"}
    elif isinstance(device, SessyCTMeter):
        return {"title": "Sessy CT"}
    else:
        return {"title": f"Sessy {device_id}"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sessy."""

    VERSION = 1

    hostname = None
    username = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        _LOGGER.info("Starting user config flow for Sessy")

        # Use discovered hostname and username if available, otherwise use defaults
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self.hostname or "sessy-"): str,
                vol.Required(CONF_USERNAME, default=self.username or vol.UNDEFINED): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=data_schema
            )

        await self.async_set_unique_id(user_input.get(CONF_USERNAME))
        self._abort_if_unique_id_configured(updates={CONF_HOST: user_input.get(CONF_HOST)})

        errors = {}

        # Attempt to connect to Sessy API
        try:
            info = await validate_input(self.hass, user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"
        else:
            # Connection was succesful, create config entry
            return self.async_create_entry(title=info["title"], data=user_input)

        # Pass errors to user and show form again
        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
    @property
    def _name(self) -> str | None:
        return self.context.get(CONF_NAME)

    @_name.setter
    def _name(self, value: str) -> None:
        self.context[CONF_NAME] = value
        self.context["title_placeholders"] = {"name": self._name}

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""

        _LOGGER.info("Starting zeroconf config flow for Sessy")
        try:
            # Get device info from zeroconf
            local_name = discovery_info.hostname[:-1]
            serial_number = discovery_info.properties.get("serial")
            _LOGGER.info(f"Discovered Sessy device at {local_name} with serial: {serial_number}")

            # Check for duplicates
            await self.async_set_unique_id(serial_number)
            self._abort_if_unique_id_configured()

            # Update the config flow title
            self._name = local_name.removesuffix(".local")

            # Update the autofill information
            self.hostname = local_name
            self.username = serial_number
        except Exception:
            return self.async_abort(reason="discovery_error")
        else:
            # Prompt user for the password
            return await self.async_step_user()
        
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return OptionsFlowHandler(config_entry)
    

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_POWER.seconds),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=300)
                    )
                }
            ),
        ) 

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

