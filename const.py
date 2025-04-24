"""Constants for the Aigües de l'Horta integration."""
from datetime import timedelta

DOMAIN = "aigues_horta"
NAME = "Aigües de l'Horta"
VERSION = "0.1.0"

DEFAULT_SCAN_INTERVAL = timedelta(hours=1)
PLATFORMS = ["sensor"]

# Attributes
ATTR_CONTRACT_NUMBER = "contract_number"
ATTR_ADDRESS = "address"
ATTR_LAST_READING_DATE = "last_reading_date"
ATTR_NEXT_READING_DATE = "next_reading_date"
ATTR_CONSUMPTION_CURRENT = "consumption_current"
ATTR_CONSUMPTION_PREVIOUS = "consumption_previous"
ATTR_CONSUMPTION_YEARLY = "consumption_yearly"
