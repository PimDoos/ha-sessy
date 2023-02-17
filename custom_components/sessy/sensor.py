"""Sensor to read vehicle data from Sessy"""
from __future__ import annotations
from homeassistant.config_entries import ConfigEntry


from homeassistant.const import (
    POWER_KILO_WATT,
    POWER_WATT,
    ENERGY_KILO_WATT_HOUR,
    PERCENTAGE
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant


from .const import DOMAIN, SESSY_DEVICE

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    SENSORS = []

   
    async_add_entities(SENSORS)
    