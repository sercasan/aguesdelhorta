# --- START OF FILE const.py (No changes needed, but for reference) ---
"""Constants for the Aigües de l'Horta integration."""
from datetime import timedelta

DOMAIN = "aigues_horta"
NAME = "Aigües de l'Horta"
VERSION = "0.1.3" # Increment version

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
PLATFORMS = ["sensor"] # Only sensor platform

# Attributes
ATTR_CONTRACT_NUMBER = "contract_number"
ATTR_ADDRESS = "address"
ATTR_LAST_READING_DATE = "last_reading_date" # Date of the latest reading used for the main state
ATTR_NEXT_READING_DATE = "next_reading_date" # (Not currently extracted)
ATTR_CONSUMPTION_CURRENT = "consumption_current" # Not used as attribute, it's the native_value
ATTR_CONSUMPTION_PREVIOUS = "consumption_previous" # (Placeholder)
ATTR_CONSUMPTION_YEARLY = "consumption_yearly" # (Placeholder)
ATTR_HOURLY_CONSUMPTION = "hourly_consumption" # Key for the hourly history dict attribute
# --- END OF FILE const.py ---
