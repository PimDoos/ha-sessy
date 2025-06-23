from datetime import timedelta

DOMAIN = "sessy"

# Default scan interval for all entities except power related
DEFAULT_SCAN_INTERVAL = timedelta(seconds=60)

# Default scan interval for power related entities, overridden by scan_interval option config flow
DEFAULT_SCAN_INTERVAL_POWER = timedelta(seconds=5)

# Static scan intervals
SCAN_INTERVAL_OTA_BUSY = timedelta(seconds=10)
SCAN_INTERVAL_OTA_CHECK = timedelta(hours=6)
SCAN_INTERVAL_SCHEDULE = timedelta(hours=1)

SESSY_DEVICE = "sessy_device"
SERIAL_NUMBER = "serial_number"
SESSY_DEVICE_INFO = "sessy_device_info"

UPDATE_TOPIC = "sessy_update_topic_{}"

TIME_TRACKER_POWER = "time_tracker_power"

SESSY_CACHE = "sessy_cache"
SESSY_CACHE_TRACKERS = "sessy_cache_trackers"
SESSY_CACHE_TRIGGERS = "sessy_cache_triggers"
SESSY_CACHE_INTERVAL = "sessy_cache_interval"

ENTITY_ERROR_THRESHOLD = 5
COORDINATOR_RETRIES = 5
COORDINATOR_RETRY_DELAY = 1
COORDINATOR_TIMEOUT = 10

SESSY_RELEASE_NOTES_URL = "https://www.sessy.nl/firmware-updates"
