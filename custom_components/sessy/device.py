"""Device info for Sessy"""

from __future__ import annotations

import logging

from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from sessypy.devices import (
    SessyBattery,
    SessyDevice,
    SessyP1Meter,
)

from .const import (
    DOMAIN,
    SESSY_MANUFACTURER,
)
from .coordinator import SessyCoordinator
from .models import SessyConfigEntry, SessyConnectedDeviceType
from .util import decode_equipment_identifier

_LOGGER = logging.getLogger(__name__)


async def generate_device_info(
    hass: HomeAssistant,
    config_entry: SessyConfigEntry,
    device: SessyDevice,
    coordinators: dict[SessyConnectedDeviceType, SessyCoordinator],
) -> dict[SessyConnectedDeviceType, DeviceInfo]:
    """Generate DeviceInfo for connected devices, if any."""

    network_status_coordinator: SessyCoordinator = coordinators.get(
        device.get_network_status, None
    )
    if network_status_coordinator is None:
        raise ConfigEntryNotReady(
            f"System info not available for {device} at {device.host}"
        )

    identifiers = {(DOMAIN, device.serial_number)}

    wifi_status = network_status_coordinator.raw_data.get("wifi_sta")
    if wifi_status is not None and "mac" in wifi_status:
        wifi_mac_address = dr.format_mac(wifi_status.get("mac"))
        identifiers.add((dr.CONNECTION_NETWORK_MAC, wifi_mac_address))

    ethernet_status = network_status_coordinator.raw_data.get("eth")
    if ethernet_status is not None and "mac" in ethernet_status:
        ethernet_mac_address = dr.format_mac(ethernet_status.get("mac"))
        identifiers.add((dr.CONNECTION_NETWORK_MAC, ethernet_mac_address))

    system_info_coordinator: SessyCoordinator = coordinators.get(
        device.get_system_info, None
    )

    if system_info_coordinator is None:
        raise ConfigEntryNotReady(
            f"System info not available for {device} at {device.host}"
        )

    device_info = dict()

    # Generate own device info
    device_info[SessyConnectedDeviceType.SELF] = DeviceInfo(
        name=device.name,
        manufacturer=SESSY_MANUFACTURER,
        identifiers=identifiers,
        configuration_url=f"http://{device.host}/",
        model=device.model,
        serial_number=device.serial_number,
    )

    if isinstance(device, SessyBattery):
        battery_serial = system_info_coordinator.raw_data.get("sessy_serial", None)
        battery_revision = system_info_coordinator.raw_data.get("sessy_revision", None)

        # Battery connected to Battery Dongle
        if battery_serial is not None and battery_revision is not None:
            battery_revision_formatted = f"{(battery_revision / 100):.2f}"

            device_info[SessyConnectedDeviceType.BATTERY] = DeviceInfo(
                name=f"Sessy Battery {battery_serial[:4]}",
                manufacturer=SESSY_MANUFACTURER,
                identifiers={(DOMAIN, battery_serial)},
                configuration_url=f"http://{device.host}/",
                model="Sessy Battery",
                hw_version=battery_revision_formatted,
                serial_number=battery_serial,
                via_device=(DOMAIN, device.serial_number),
            )

    elif isinstance(device, SessyP1Meter):
        p1_coordinator = coordinators.get(device.get_p1_details, None)

        # Equipment connected to P1 port
        if p1_coordinator is not None:
            p1_serial_dec = p1_coordinator.raw_data.get("equipment_identifier", None)
            p1_model = p1_coordinator.raw_data.get("header_info", None)
            p1_revision = p1_coordinator.raw_data.get("dsmr_version", None)

            if (
                p1_serial_dec is not None
                and p1_model is not None
                and p1_revision is not None
            ):
                p1_revision_formatted = f"DSMR {(p1_revision / 10):.1f}"
                p1_serial = decode_equipment_identifier(p1_serial_dec)

                device_info[SessyConnectedDeviceType.P1_METER] = DeviceInfo(
                    name="P1 Electricity meter",
                    manufacturer=None,
                    identifiers={(DOMAIN, p1_serial)},
                    configuration_url=f"http://{device.host}/",
                    model=p1_model,
                    hw_version=p1_revision_formatted,
                    serial_number=p1_serial,
                    via_device=(DOMAIN, device.serial_number),
                )

            gas_serial_dec = p1_coordinator.raw_data.get(
                "gas_equipment_identifier", None
            )

            if gas_serial_dec is not None:
                gas_serial = decode_equipment_identifier(gas_serial_dec)

                if len(gas_serial) > 8:
                    device_info[SessyConnectedDeviceType.P1_GAS_METER] = DeviceInfo(
                        name="P1 Gas meter",
                        manufacturer=None,
                        identifiers={(DOMAIN, gas_serial)},
                        configuration_url=f"http://{device.host}/",
                        serial_number=gas_serial,
                        via_device=(DOMAIN, device.serial_number),
                    )

        modbus_coordinator = coordinators.get(device.get_modbus_details, None)

        # Equipment connected via Modbus
        if modbus_coordinator is not None:
            modbus_model: str = modbus_coordinator.raw_data.get("device_type", None)
            modbus_serial: str = modbus_coordinator.raw_data.get("device_uid", None)

            if modbus_model is not None:
                device_info[SessyConnectedDeviceType.MODBUS_METER] = DeviceInfo(
                    name=f"{modbus_model}",
                    manufacturer=None,
                    identifiers={(DOMAIN, modbus_serial)},
                    configuration_url=f"http://{device.host}/",
                    model=modbus_model,
                    serial_number=modbus_serial,
                    via_device=(DOMAIN, device.serial_number),
                )

    return device_info


def update_sw_version(
    hass,
    config_entry: SessyConfigEntry,
    new_version: str,
    connected_device_type: SessyConnectedDeviceType = SessyConnectedDeviceType.SELF,
):
    try:
        device_info = config_entry.runtime_data.device_info.get(connected_device_type)
        device_registry = dr.async_get(hass)
        device = device_registry.async_get_device(device_info[ATTR_IDENTIFIERS])
        device_registry.async_update_device(device.id, sw_version=new_version)
    except Exception as e:
        _LOGGER.warning(
            "Could not write new software version to device registry: %s", e
        )
