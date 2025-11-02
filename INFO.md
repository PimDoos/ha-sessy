# Sessy Home Assistant integration
Sessy Custom Component for Home Assistant.

Currently supported features:

## All devices
- Firmware updates
- Dongle network status
- Dongle reboot

## Sessy Battery
- Power Status
- System State
- Output Power (W)
- Power Setpoint (W)
- Renewable Energy Meter
  - Power (W)
  - Current (A)
  - Voltage (V)

- Power Strategy
  - Get and set strategy via select entity

- Power Setpoint
  - Get and set via number entity

- Configuration
  - Min/max power
  - Start/stop times

- Schedules
  - Read energy prices
  - Read dynamic mode power schedule

## Sessy Meter

### Sessy P1 Dongle
- P1 Status
  - Net power flow
  - Per phase current, voltage, power (consumption/production)
  - Active tariff
  - Tariff energy meters (consumption/production)

- NOM Coordinator controls
  - Grid Target via number entity (X on the meter)

- Network Status
  - WiFi RSSI (dBm)

- Firmware updates

### Sessy CT Dongle
- Net power flow
- Per phase current, voltage, power (consumption/production)
- NOM Coordinator controls
  - Grid Target via number entity (X on the meter)