"""Sensor platform for Aigües de l'Horta integration."""
import logging
from typing import Callable, Dict, Optional, Any
from collections import OrderedDict
from datetime import datetime

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfVolume
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util # For timezone handling

from .const import (
    ATTR_ADDRESS, ATTR_CONTRACT_NUMBER,
    ATTR_HOURLY_CONSUMPTION, DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aigües de l'Horta sensors."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    sensors = [
        AiguesHortaMeterReadingSensor(coordinator, entry), # Renamed for clarity
        AiguesHortaHourlyConsumptionSensor(coordinator, entry)
    ]
    async_add_entities(sensors, True)


# Renamed for clarity vs Hourly Consumption
class AiguesHortaMeterReadingSensor(CoordinatorEntity, SensorEntity):
    """Sensor representing the latest water meter reading."""
    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL_INCREASING # Correct for meter reading
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_icon = "mdi:counter"

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry; self._attrs = {}
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_meter_reading" # Stable ID
        self._contract_id = coordinator.data.get("contract_number", entry.entry_id) if coordinator.data else entry.entry_id
        base_name = f"Aigües de l'Horta {entry.title}"
        self._attr_name = f"{base_name} Meter Reading"
        self._attr_device_info = { # Device info using contract_id
            "identifiers": {(DOMAIN, self._contract_id)}, "name": base_name,
            "manufacturer": "Aigües de l'Horta",
            "model": f"Meter ({self._contract_id})" if self._contract_id != entry.entry_id else "Meter",
            "entry_type": "service",
        }
        if coordinator.data: self._update_attrs()

    @property
    def native_value(self) -> StateType:
        """Return the state (latest meter reading)."""
        if self.coordinator.data: return self.coordinator.data.get("current_consumption")
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return self._attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        # Update device info if contract ID changes
        if self.coordinator.data:
            new_contract_id = self.coordinator.data.get("contract_number", self._entry.entry_id)
            if self._contract_id != new_contract_id:
                 self._contract_id = new_contract_id
                 self._attr_device_info["identifiers"] = {(DOMAIN, self._contract_id)}
                 self._attr_device_info["model"] = f"Meter ({self._contract_id})" if self._contract_id != self._entry.entry_id else "Meter"
        self._update_attrs()
        self.async_write_ha_state()

    def _update_attrs(self) -> None:
        """Update sensor attributes."""
        attrs = {}
        if self.coordinator.data:
            data = self.coordinator.data
            attrs[ATTR_CONTRACT_NUMBER] = data.get("contract_number")
            attrs[ATTR_ADDRESS] = data.get("address")
            attrs["last_reading_date"] = data.get("last_reading_date") # Date of latest reading
            # Optionally add hourly CONSUMPTION history here too, or keep it only on the hourly sensor?
            # Let's keep it simpler for this sensor for now.
        self._attrs = attrs


class AiguesHortaHourlyConsumptionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for the water consumption during the most recent hour."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    # *** CORRECTION: Use TOTAL as it represents consumption *during* the hour ***
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = UnitOfVolume.CUBIC_METERS
    _attr_icon = "mdi:water-pump" # Icon suggesting flow/usage

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._entry = entry; self._attrs = {}
        # Keep track of the timestamp string for the current value
        self._current_value_timestamp_str: Optional[str] = None
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_hourly_consumption" # Stable ID
        self._contract_id = coordinator.data.get("contract_number", entry.entry_id) if coordinator.data else entry.entry_id
        base_name = f"Aigües de l'Horta {entry.title}"
        self._attr_name = f"{base_name} Hourly Consumption"
        self._attr_device_info = { # Link to the same device
            "identifiers": {(DOMAIN, self._contract_id)}, "name": base_name,
            "manufacturer": "Aigües de l'Horta",
            "model": f"Meter ({self._contract_id})" if self._contract_id != self._entry.entry_id else "Meter",
        }
        if coordinator.data: self._update_attrs()

    @property
    def native_value(self) -> StateType:
        """Return the state (consumption amount for the last hour)."""
        latest_value = None
        new_timestamp_str = None # Store the timestamp associated with this value
        if self.coordinator.data and ATTR_HOURLY_CONSUMPTION in self.coordinator.data:
            hourly_data = self.coordinator.data[ATTR_HOURLY_CONSUMPTION]
            if isinstance(hourly_data, dict) and hourly_data:
                try:
                    valid_keys = sorted([k for k in hourly_data.keys() if isinstance(k, str)])
                    if valid_keys:
                        latest_timestamp_str = valid_keys[-1]
                        latest_value = hourly_data[latest_timestamp_str]
                        new_timestamp_str = latest_timestamp_str # Found timestamp for current value
                except Exception as e: _LOGGER.debug("Error getting latest hourly value: %s.", e)

        # Store the timestamp string internally to be used by last_reset
        self._current_value_timestamp_str = new_timestamp_str
        return latest_value

    # *** REINTRODUCED last_reset PROPERTY ***
    @property
    def last_reset(self) -> datetime | None:
        """Return the start time of the hourly interval for the current value."""
        # If the native_value represents consumption from 10:00 to 11:00,
        # last_reset should be the datetime object for 10:00:00.
        if self._current_value_timestamp_str:
            try:
                # The timestamp string (e.g., "2025-04-26T10:00:00") IS the start of the hour.
                dt_object = dt_util.parse_datetime(self._current_value_timestamp_str)
                # Ensure it's timezone-aware if possible (using HA's timezone)
                # return dt_util.as_local(dt_object) if dt_object else None # Might cause issues if naive
                return dt_object # Return the parsed datetime object
            except (ValueError, TypeError):
                 _LOGGER.warning("Could not parse timestamp for last_reset: '%s'", self._current_value_timestamp_str)
                 return None
        _LOGGER.debug("last_reset is None because _current_value_timestamp_str is None")
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return the state attributes."""
        return self._attrs

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data."""
        # Update device info if contract ID changes
        if self.coordinator.data:
            new_contract_id = self.coordinator.data.get("contract_number", self._entry.entry_id)
            if self._contract_id != new_contract_id:
                 self._contract_id = new_contract_id
                 self._attr_device_info["identifiers"] = {(DOMAIN, self._contract_id)}
                 self._attr_device_info["model"] = f"Meter ({self._contract_id})" if self._contract_id != self._entry.entry_id else "Meter"

        self._update_attrs()
        # Value and last_reset are calculated dynamically by properties when state is written
        self.async_write_ha_state()

    def _update_attrs(self) -> None:
        """Update sensor attributes."""
        attrs = {}
        if self.coordinator.data:
            data = self.coordinator.data
            attrs[ATTR_CONTRACT_NUMBER] = data.get("contract_number")
            attrs[ATTR_ADDRESS] = data.get("address")

            # Add hourly consumption history
            hourly_data = data.get(ATTR_HOURLY_CONSUMPTION)
            if isinstance(hourly_data, dict) and hourly_data:
                try:
                    valid_keys = sorted([k for k in hourly_data.keys() if isinstance(k, str)], reverse=True)[:24]
                    sorted_hourly_history = OrderedDict((k, hourly_data[k]) for k in valid_keys)
                    attrs["hourly_consumption_history"] = dict(sorted_hourly_history)
                    # Add timestamp of the latest data point in history (same as used for native_value)
                    if valid_keys: attrs["last_updated_hour"] = valid_keys[0]
                except Exception as e:
                     _LOGGER.error("Error processing hourly attrs: %s", e)
                     attrs["hourly_consumption_history"] = "Error"
            else: attrs["hourly_consumption_history"] = {}
        self._attrs = attrs

# --- END OF FILE sensor.py ---
