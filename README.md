# ha-sessy
Home Assistant integration for Sessy home battery system.
Work in progress :)

Currently supported:
- Connect to Battery or P1 Dongle
- Power Status sensors
- Wifi RSSI sensor (Battery only)
- P1 Status sensors (P1 Dongle only)

TODO:
- [X] Add Power Status sensors
- [ ] Add Power Strategy sensors
- [ ] Add Power Setpoint service
- [ ] Add Power Strategy service
- [ ] Add Energy sensors
- [ ] Add update entities
- [X] Add Device Registry information
- [ ] Add logo to home-assistant/brands
- [ ] Add HACS configuration

Installation
============

HACS
----
Not available yet

Manual
------
- Copy the `custom_components/sessy` folder to the `custom_components` folder in your configuration directory.
- Install the sessypy module in Home Assistant's VENV or copy the [`sessypy`](https://github.com/PimDoos/sessypy/tree/main/src/sessypy) module folder to the `custom_components/sessy` folder.
