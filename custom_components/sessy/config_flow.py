"""Config flow for Sessy integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from homeassistant.const import (
    CONF_PASSWORD,
    CONF_USERNAME,
    CONF_HOST
)
from homeassistant.helpers import device_registry as dr

from sessypy.devices import get_sessy_device, SessyBattery, SessyP1Meter
from sessypy.util import SessyConnectionException, SessyLoginException

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """

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
    
    
    # Return info that you want to store in the config entry.
    if isinstance(device, SessyBattery):
        return {"title": "Sessy Battery"}
    elif isinstance(device, SessyP1Meter):
        return {"title": "Sessy P1"}
    else:
        return {"title": "Sessy"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Sessy."""

    VERSION = 1


    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        data_schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=data_schema
            )

        errors = {}

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
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=errors
        )
    
    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        try:
            local_name = discovery_info.hostname[:-1]
            serial_number = discovery_info.properties.get("serial")
            _LOGGER.info(f"Discovered Sessy device at {local_name} with serial: {serial_number}")
            


            self._abort_if_unique_id_configured(updates={CONF_HOST: local_name})
            for ip_address in discovery_info.addresses:
                self._abort_if_unique_id_configured(updates={CONF_HOST: ip_address})

            data_schema = vol.Schema(
                {
                    vol.Required(CONF_HOST, default=local_name): str,
                    vol.Required(CONF_USERNAME, default=serial_number): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            )

            return self.async_show_form(
                step_id="user", data_schema=data_schema
            )
    
        except:
            self.async_abort(reason="")
        



class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
