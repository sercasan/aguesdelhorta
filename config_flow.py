"""Config flow for Aigües de l'Horta integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN
from .aigues_horta_api import AiguesHortaAPI

_LOGGER = logging.getLogger(__name__)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required("username"): str,
        vol.Required("password"): str,
    }
)


async def validate_input(hass: HomeAssistant, data: dict) -> dict:
    """Validate the user input allows us to connect."""
    
    api = AiguesHortaAPI(data["username"], data["password"])
    
    try:
        # Test the login credentials
        await hass.async_add_executor_job(api.login)
    except Exception as err:
        _LOGGER.error("Error validating login: %s", err)
        raise InvalidAuth from err
    
    # Get account info for title
    try:
        account_info = await hass.async_add_executor_job(api.get_account_info)
        title = account_info.get("name", data["username"])
    except Exception:
        title = data["username"]
    
    return {"title": title}


class AiguesHortaConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Aigües de l'Horta."""

    VERSION = 1
    
    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}
        
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
                
                return self.async_create_entry(title=info["title"], data=user_input)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
                
        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
