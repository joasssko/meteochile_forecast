"""Config flow for MeteoChile Weather integration."""
from __future__ import annotations
from typing import Any
import re
import html
import logging
import voluptuous as vol
import aiohttp
import async_timeout

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_NAME, API_URL, CITIES

_LOGGER = logging.getLogger(__name__)

async def async_fetch_cities(session: aiohttp.ClientSession) -> dict[str, str]:
    """Fetch the list of cities from MeteoChile."""
    try:
        async with async_timeout.timeout(10):
            response = await session.get(API_URL)
            response.raise_for_status()
            content = await response.text()
            
            # Find all blocks between Pronostico.push( and );
            blocks_raw = re.findall(r'Pronostico\.push\((.*?)\);', content, re.DOTALL)
            fetched_cities = {}
            for block in blocks_raw:
                ind = re.search(r'indice\s*:\s*"(.*?)"', block)
                ciu = re.search(r'ciudad\s*:\s*"(.*?)"', block)
                if ind and ciu:
                    fetched_cities[ind.group(1)] = html.unescape(ciu.group(1))
            
            if fetched_cities:
                return fetched_cities
    except Exception as err:
        _LOGGER.warning("Failed to fetch cities from MeteoChile, using fallback list: %s", err)
    
    return CITIES

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for MeteoChile Weather."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        # Fetch cities to display in dropdown
        session = async_get_clientsession(self.hass)
        cities = await async_fetch_cities(session)
        
        # Sort cities alphabetically by name
        sorted_cities = sorted(cities.items(), key=lambda x: x[1])
        city_options = {k: v for k, v in sorted_cities}

        if user_input is not None:
            try:
                city_id = user_input[CONF_CITY_ID]
                city_name = city_options.get(city_id, CITIES.get(city_id, city_id))
                
                # Check if already configured
                await self.async_set_unique_id(city_id)
                self._abort_if_unique_id_configured()
                
                # Store city_name in entry data
                user_input[CONF_CITY_NAME] = city_name
                
                return self.async_create_entry(title=city_name, data=user_input)
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        schema = vol.Schema(
            {
                vol.Required(CONF_CITY_ID): vol.In(city_options),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )
