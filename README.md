# ha-sessy
Home Assistant integration for Sessy home battery system.
Work in progress :)

Currently supported:
- Connect to Battery or P1 Dongle
- Power Status sensors
- Set power strategy (select entity)
- Set power setpoint (number entity)
- Wifi RSSI sensor (Battery only)
- P1 Status sensors (P1 Dongle only)
- Firmware updates
- Change configuration (min/max power)

TODO:
- [X] Add Power Status sensors
- [X] Add Power Strategy select
- [X] Add Power Setpoint number entity
- [ ] Add Energy sensors
- [X] Add update entities
- [X] Add Device Registry information
- [X] Add logo to home-assistant/brands
- [X] Add HACS configuration
- [ ] Add to HACS Default repository

Installation
============

HACS
----
Add this repository to HACS via the Custom Repositories options

Manual
------
- Copy the `custom_components/sessy` folder to the `custom_components` folder in your configuration directory.

Configuration
=============
Add Sessy via the Integrations menu: 

- Go to Integrations > Add Integrations > Sessy

  [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=sessy)

- Enter the IP address (preferably static) or hostname and the local username and password for the device you want to add

- The integration will discover the device type and add it to Home Assistant

