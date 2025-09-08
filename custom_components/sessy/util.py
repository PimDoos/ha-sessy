from __future__ import annotations
from datetime import datetime, time
from enum import Enum
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

from homeassistant.helpers.entity import DeviceInfo

from sessypy.devices import SessyDevice, SessyBattery, SessyP1Meter, SessyCTMeter

from typing import Callable, Optional

from .const import DOMAIN

import logging
_LOGGER = logging.getLogger(__name__)



# Transform functions

def backend_status_string(status_string: str, prefix: str = "") -> str:
    return status_string.removeprefix(prefix).lower()

def status_string_p1(status_string: str) -> str:
    return backend_status_string(status_string, "P1_")

def status_string_system_state(status_string: str) -> str:
    return backend_status_string(status_string, "SYSTEM_STATE_")

def status_string_power_strategy(status_string: str) -> str:
    return backend_status_string(status_string, "POWER_STRATEGY_")

def divide_by_thousand(input: int) -> float:
    return input / 1000

def divide_by_hundred_thousand(input: int) -> float:
    return input / 100000

def only_negative_as_positive(input: int) -> int:
    return min(input, 0) * -1

def only_positive(input: int) -> int:
    return max(input, 0)

def time_from_string(input: str) -> time:
    return datetime.strptime(input, "%H:%M").time()

def start_time_from_string(input: str) -> time:
    return time_from_string(input.split("-")[0])

def stop_time_from_string(input: str) -> time:
    return time_from_string(input.split("-")[1])

def transform_on_list(transform_list: list, transform_function: Callable) -> list:
    transformed = []
    for i in transform_list:
        transformed.append(
            transform_function(i)
        )
    return transformed


def enum_to_options_list(options: Enum, transform_function: Optional[Callable] = None) -> list[str]:
    output = list()
    for option in options:
        value = option.value
        if transform_function:
            output.append(transform_function(value))
        else:
            output.append(value)
    return output


def unit_interval_to_percentage(input: float) -> float:
    return round(input * 100,1)

# End transform functions


async def generate_device_info(hass: HomeAssistant, config_entry: ConfigEntry, device: SessyDevice) -> DeviceInfo:
    
    model = "Sessy Device"
    if isinstance(device, SessyBattery):
        model = "Sessy Battery"
    elif isinstance(device, SessyP1Meter):
        model = "Sessy P1 Dongle"
    elif isinstance(device, SessyCTMeter):
        model = "Sessy CT Dongle"

    # Generate Device Info
    device_info = DeviceInfo(
        name=device.name,
        manufacturer="Charged B.V.",
        identifiers={(DOMAIN, device.serial_number)},
        configuration_url=f"http://{device.host}/",
        model=model,
        serial_number=device.serial_number,
    )

    return device_info

def get_nested_key(data, key):
    if data == None:
        return None
    elif len(data) == 0:
        return None
    elif key == None or len(key) == 0:
        return data
    else:
        value = data
        node: str
        for node in key.split("."):
            if node.isdigit():
                node = int(node)
            if value == None:
                return None
            elif node in value:
                value = value[node]
                continue
            else:
                value = None
    return value
