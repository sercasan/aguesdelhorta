"""Sensor platform for Aigües de l'Horta integration."""
import logging
from typing import Callable, Dict, Optional

from homeassistant.components.sensor import (
    SensorEntity,
    SensorDeviceClass,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import VOLUME_CUBIC_METERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    ATTR_ADDRESS,
    ATTR_CONTRACT_NUMBER,
    ATTR_CONSUMPTION_CURRENT,
    ATTR_CONSUMPTION_PREVIOUS,
    ATTR_CONSUMPTION_YEARLY,
    ATTR_LAST_READING_DATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Aigües de l'Horta sensors from config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    
    sensors = []
    
    # Add water consumption sensor
    sensors.append(AiguesHortaConsumptionSensor(coordinator, entry))
    
    # Add more sensors if you want to track other data points
    
    async_add_entities(sensors, True)


class AiguesHortaConsumptionSensor(CoordinatorEntity, SensorEntity):
    """Sensor for water consumption."""

    _attr_has_entity_name = True
    _attr_device_class = SensorDeviceClass.WATER
    _attr_state_class = SensorStateClass.TOTAL
    _attr_native_unit_of_measurement = VOLUME_CUBIC_METERS
    
    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_water_consumption"
        self._entry = entry
        
        # Set sensor name
        self._attr_name = "Water Consumption"
        
        # Device info
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Aigües de l'Horta {entry.title}",
            "manufacturer": "Aigües de l'Horta",
            "model": "Water Meter",
        }
    
    @property
    def native_value(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data:
            return self.coordinator.data.get("current_consumption")
        return None
    
    @property
    def extra_state_attributes(self) -> Dict[str, any]:
        """Return the state attributes."""
        attrs = {}

        if self.coordinator.data:
            data = self.coordinator.data
            
            if "contract_number" in data:
                attrs[ATTR_CONTRACT_NUMBER] = data["contract_number"]
                
            if "address" in data:
                attrs[ATTR_ADDRESS] = data["address"]
                
            if "last_reading_date" in data:
                attrs[ATTR_LAST_READING_DATE] = data["last_reading_date"]
                
            if "previous_consumption" in data:
                attrs[ATTR_CONSUMPTION_PREVIOUS] = data["previous_consumption"]
                
            if "yearly_consumption" in data:
                attrs[ATTR_CONSUMPTION_YEARLY] = data["yearly_consumption"]
        
        return attrs
