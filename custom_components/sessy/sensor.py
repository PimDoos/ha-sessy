"""Sensor to read data from Sessy"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfPower,
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfElectricCurrent,
    UnitOfInformation,
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    UnitOfFrequency
)
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory

from sessypy.const import SessyApiCommand, SessySystemState, SessyP1State
from sessypy.devices import SessyBattery, SessyDevice, SessyP1Meter, SessyCTMeter


from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, SESSY_DEVICE, SCAN_INTERVAL_POWER
from .util import (add_cache_command, enum_to_options_list, status_string_p1, status_string_system_state, 
                   unit_interval_to_percentage, divide_by_thousand, only_negative_as_positive, only_positive)
from .sessyentity import SessyEntity

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities):
    """Set up the Sessy sensors"""

    device = hass.data[DOMAIN][config_entry.entry_id][SESSY_DEVICE]
    sensors = []

    sensors.append(
        SessySensor(hass, config_entry, "WiFi RSSI",
                    SessyApiCommand.NETWORK_STATUS, "wifi_sta.rssi",
                    SensorDeviceClass.SIGNAL_STRENGTH, SensorStateClass.MEASUREMENT, SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
                    entity_category=EntityCategory.DIAGNOSTIC)
    )

    for memory_type in ("internal","external"):
        sensors.append(
            SessySensor(hass, config_entry, f"{ memory_type.title() } Memory Available",
                        SessyApiCommand.SYSTEM_INFO, f"{ memory_type }_mem_available",
                        SensorDeviceClass.DATA_SIZE, SensorStateClass.MEASUREMENT, UnitOfInformation.BYTES,
                        entity_category=EntityCategory.DIAGNOSTIC)

        )

    if isinstance(device, SessyBattery):
        sensors.append(
            SessySensor(hass, config_entry, "System State",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state",
                        SensorDeviceClass.ENUM,
                        translation_key = "battery_system_state", transform_function=status_string_system_state,
                        options = enum_to_options_list(SessySystemState, status_string_system_state))
        )
        sensors.append(
            SessySensor(hass, config_entry, "System State Details",
                        SessyApiCommand.POWER_STATUS, "sessy.system_state_details",
                        entity_category=EntityCategory.DIAGNOSTIC)
        )
        sensors.append(
            SessySensor(hass, config_entry, "State of Charge",
                        SessyApiCommand.POWER_STATUS, "sessy.state_of_charge",
                        SensorDeviceClass.BATTERY, SensorStateClass.MEASUREMENT, PERCENTAGE,
                        transform_function=unit_interval_to_percentage, precision = 1)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Charge Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                        transform_function=only_negative_as_positive)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Discharge Power",
                        SessyApiCommand.POWER_STATUS, "sessy.power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT,
                        transform_function=only_positive)
        )
        sensors.append(
            SessySensor(hass, config_entry, "Frequency",
                        SessyApiCommand.POWER_STATUS, "sessy.frequency",
                        SensorDeviceClass.FREQUENCY, SensorStateClass.MEASUREMENT, UnitOfFrequency.HERTZ,
                        transform_function=divide_by_thousand, precision = 3)
        )
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Voltage",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.voltage_rms",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.MILLIVOLT,
                            suggested_unit_of_measurement=UnitOfElectricPotential.VOLT)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Current",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.current_rms",
                            SensorDeviceClass.CURRENT, SensorStateClass.MEASUREMENT, UnitOfElectricCurrent.MILLIAMPERE,
                            suggested_unit_of_measurement=UnitOfElectricCurrent.AMPERE)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Renewable Energy Phase { phase_id } Power",
                            SessyApiCommand.POWER_STATUS, f"renewable_energy_phase{ phase_id }.power",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.WATT)
            )


    elif isinstance(device, SessyP1Meter):
        sensors.append(
            SessySensor(hass, config_entry, "P1 Power",
                        SessyApiCommand.P1_DETAILS, "total_power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT, precision = 3)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Consuming Power",
                        SessyApiCommand.P1_DETAILS, "power_consumed",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT, precision = 3)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Producing Power",
                        SessyApiCommand.P1_DETAILS, "power_produced",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT, precision = 3)
        )
        sensors.append(
            SessySensor(hass, config_entry, "P1 Status",
                        SessyApiCommand.P1_DETAILS, "state",
                        SensorDeviceClass.ENUM,
                        translation_key = "p1_state", transform_function=status_string_p1,
                        options = enum_to_options_list(SessyP1State, status_string_p1)
                        )
        )
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            SessyApiCommand.P1_DETAILS, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, precision = 2)
            )

    elif isinstance(device, SessyCTMeter):
        sensors.append(
            SessySensor(hass, config_entry, "Total Power",
                        SessyApiCommand.P1_DETAILS, "total_power",
                        SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT, precision = 3)
        )
        for phase_id in range(1,4):
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Voltage",
                            SessyApiCommand.P1_DETAILS, f"voltage_l{ phase_id }",
                            SensorDeviceClass.VOLTAGE, SensorStateClass.MEASUREMENT, UnitOfElectricPotential.VOLT, precision = 2)
            )
            sensors.append(
                SessySensor(hass, config_entry, f"Phase { phase_id } Power",
                            SessyApiCommand.P1_DETAILS, f"power_l{ phase_id }",
                            SensorDeviceClass.POWER, SensorStateClass.MEASUREMENT, UnitOfPower.KILO_WATT, precision = 3)
            )

    async_add_entities(sensors)

class SessySensor(SessyEntity, SensorEntity):
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry, name: str,
                 cache_command: SessyApiCommand, cache_key,
                 device_class: SensorDeviceClass = None, state_class: SensorStateClass = None, unit_of_measurement = None,
                 transform_function: function = None, translation_key: str = None,
                 options = None, entity_category: EntityCategory = None, precision: int = None, suggested_unit_of_measurement = None):

        super().__init__(hass=hass, config_entry=config_entry, name=name,
                       cache_command=cache_command, cache_key=cache_key,
                       transform_function=transform_function, translation_key=translation_key)

        self._attr_device_class = device_class
        self._attr_state_class = state_class
        self._attr_native_unit_of_measurement = unit_of_measurement
        self._attr_entity_category = entity_category

        self._attr_suggested_display_precision = precision
        self._attr_suggested_unit_of_measurement = suggested_unit_of_measurement

        self._attr_options = options

    def update_from_cache(self):
        self._attr_available = self.cache_value != None
        self._attr_native_value = self.cache_value
