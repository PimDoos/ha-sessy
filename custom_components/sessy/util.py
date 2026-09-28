"""Shared utility functions for Sessy integration"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime, time
from enum import Enum

_LOGGER = logging.getLogger(__name__)


# Transform functions
def backend_status_string(status_string: str, prefix: str = "") -> str:
    """Convert a Sessy state machine string to a standardized lowercase string"""
    return status_string.removeprefix(prefix).lower()


def status_string_p1(status_string: str) -> str:
    """Extract status from a Sessy P1 meter status string"""
    return backend_status_string(status_string, "P1_")


def status_string_modbus(status_string: str) -> str:
    """Extract modbus state from a Sessy modbus status string"""
    return backend_status_string(status_string, "MODBUS_")


def status_string_system_state(status_string: str) -> str:
    """Extract system state from a Sessy system state string"""
    return backend_status_string(status_string, "SYSTEM_STATE_")


def status_string_power_strategy(status_string: str) -> str:
    """Extract power strategy from a Sessy power strategy string"""
    return backend_status_string(status_string, "POWER_STRATEGY_")


def divide_by_thousand(value: int) -> float:
    """Divide a value by 1000"""
    return value / 1000


def divide_by_hundred_thousand(value: int) -> float:
    """Divide a value by 100000"""
    return value / 100000


def only_negative_as_positive(value: int) -> int:
    """Return the positive value if the input is negative, otherwise return 0"""
    return min(value, 0) * -1


def only_positive(value: int) -> int:
    """Return the positive value if the input is positive, otherwise return 0"""
    return max(value, 0)


def time_from_string(value: str) -> time:
    """Convert a string in the format HH:MM to a time object"""
    return datetime.strptime(value, "%H:%M").time()  # noqa: DTZ007


def start_time_from_string(value: str) -> time:
    """Extract the start time from a string in the format HH:MM-HH:MM"""
    return time_from_string(value.split("-")[0])


def stop_time_from_string(value: str) -> time:
    """Extract the stop time from a string in the format HH:MM-HH:MM"""
    return time_from_string(value.split("-")[1])


def transform_on_list(transform_list: list, transform_function: Callable) -> list:
    """Apply a transformation function to each element in a list"""
    transformed = []
    for i in transform_list:
        transformed.append(transform_function(i))
    return transformed


def enum_to_options_list(
    options: Enum, transform_function: Callable | None = None
) -> list[str]:
    """Convert an Enum to a list of options, applying an optional transformation function"""
    output = []
    for option in options:
        value = option.value
        if transform_function:
            output.append(transform_function(value))
        else:
            output.append(value)
    return output


def unit_interval_to_percentage(value: float) -> float:
    """Convert a unit interval (0.0 to 1.0) to a percentage (0.0 to 100.0)"""
    return round(value * 100, 1)


# End transform functions


def decode_equipment_identifier(equipment_identifier_decimal: str) -> str:
    """Decode DSMR equipment identifier from decimal string"""
    equipment_identifier = ""
    for i in range(0, len(equipment_identifier_decimal), 2):
        byte = equipment_identifier_decimal[i : i + 2]
        equipment_identifier += chr(int(byte, 16))
    return equipment_identifier


def get_nested_key(data, key):
    """Retrieve a nested value from a dictionary using a path key"""
    if data is None or len(data) == 0:
        return None
    elif key is None or len(key) == 0:
        return data
    else:
        value = data
        node: str
        for node in key.split("."):
            if node.isdigit():
                node = int(node)
            if value is None:
                return None
            elif node in value:
                value = value[node]
                continue
            else:
                value = None
    return value
