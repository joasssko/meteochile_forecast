"""DataUpdateCoordinator for MeteoChile Weather."""
from __future__ import annotations

import logging
import re
import html
import json
from datetime import timedelta, datetime

import aiohttp
import async_timeout

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, CONF_CITY_ID, CONF_CITY_NAME, DEFAULT_SCAN_INTERVAL, API_URL

_LOGGER = logging.getLogger(__name__)

CONDITION_MAP = {
    "despejado": "sunny",
    "despejadonoche": "clear-night",
    "parcial": "partlycloudy",
    "parcialnoche": "partlycloudy",
    "parcialalta": "partlycloudy",
    "parcialaltanoche": "partlycloudy",
    "cubierto": "cloudy",
    "nublado": "cloudy",
    "llovizna": "rainy",
    "lluvia_debil": "rainy",
    "chubascos": "rainy",
    "lluvia": "rainy",
    "lluvia_moderada": "rainy",
    "lluvia_fuerte": "rainy",
    "nieve": "snowy",
    "chubascos_nieve": "snowy",
    "vientonieve": "snowy-rainy",
    "lluvianieve": "snowy-rainy",
    "tormenta": "lightning",
    "tormentaelectrica": "lightning",
    "nieveelectrica": "lightning-rainy",
    "tormentaarena": "exceptional",
    "viento": "windy",
    "viento3": "windy",
    "nubladoniebla": "fog",
    "nubladonieblanoche": "fog",
    "niebla": "fog",
    "neblina": "fog",
}

CONDITION_PRIORITY = [
    "lightning-rainy",
    "lightning",
    "snowy-rainy",
    "snowy",
    "pouring",
    "rainy",
    "exceptional",
    "fog",
    "windy-variant",
    "windy",
    "cloudy",
    "partlycloudy",
    "sunny",
    "clear-night"
]

def map_condition(icon_name: str) -> str | None:
    """Map MeteoChile weather icons to Home Assistant condition strings."""
    if not icon_name:
        return None
    name = icon_name.lower().replace(".png", "").strip()
    if name in CONDITION_MAP:
        return CONDITION_MAP[name]
    
    # Substring checks
    if "despejado" in name:
        if "noche" in name:
            return "clear-night"
        return "sunny"
    if "parcial" in name or "nubosidad" in name:
        return "partlycloudy"
    if "cubierto" in name or "nublado" in name:
        return "cloudy"
    if "llovizna" in name or "lluvia" in name or "chubasco" in name:
        if "nieve" in name:
            return "snowy-rainy"
        return "rainy"
    if "nieve" in name:
        if "electrica" in name:
            return "lightning-rainy"
        return "snowy"
    if "tormenta" in name:
        if "arena" in name or "polvo" in name:
            return "exceptional"
        return "lightning"
    if "viento" in name:
        return "windy"
    if "niebla" in name or "neblina" in name:
        return "fog"
    return None

def get_representative_condition(icon_list: list[str]) -> str | None:
    """Determine the most representative condition for a day from a list of icons."""
    conditions = []
    for icon in icon_list:
        cond = map_condition(icon)
        if cond:
            conditions.append(cond)
    
    if not conditions:
        return None
        
    best_cond = None
    best_priority = len(CONDITION_PRIORITY)
    for cond in conditions:
        try:
            priority = CONDITION_PRIORITY.index(cond)
            if priority < best_priority:
                best_priority = priority
                best_cond = cond
        except ValueError:
            pass
            
    return best_cond or conditions[0]

def parse_temp_range(temp_str: str) -> tuple[float | None, float | None]:
    """Parse temperatures formatted as min/max."""
    if not temp_str:
        return None, None
    parts = temp_str.split("/")
    if len(parts) == 2:
        try:
            return float(parts[0]), float(parts[1])
        except ValueError:
            pass
    elif len(parts) == 1:
        try:
            return None, float(parts[0])
        except ValueError:
            pass
    return None, None

class MeteoChileCoordinator(DataUpdateCoordinator):
    """Class to manage fetching forecast data from MeteoChile."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.city_id = entry.data[CONF_CITY_ID]
        self.city_name = entry.data.get(CONF_CITY_NAME, self.city_id)
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )

    async def _async_update_data(self) -> dict:
        """Fetch data from the endpoint."""
        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(API_URL)
                response.raise_for_status()
                content = await response.text()
                return self._parse_data(content)
                
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")

    def _parse_data(self, content: str) -> dict:
        """Parse the JS file content."""
        blocks_raw = re.findall(r'Pronostico\.push\((.*?)\);', content, re.DOTALL)
        
        keys = [
            "indice", "ciudad", "region", "fechasql", "fechasqlredaccion", 
            "tope", "icono_resto_dia", "texto_resto_dia", "fecha_resto_dia", 
            "fecha", "temperatura", "icono", "texto", "redaccion"
        ]
        
        target_city = None
        for block in blocks_raw:
            ind_match = re.search(r'indice\s*:\s*"(.*?)"', block)
            if ind_match and ind_match.group(1).strip() == self.city_id:
                # Format to JSON by quoting keys
                json_str = block.strip()
                for key in keys:
                    json_str = re.sub(rf'\b{key}\s*:', f'"{key}":', json_str)
                
                try:
                    target_city = json.loads(json_str)
                    break
                except json.JSONDecodeError as err:
                    _LOGGER.error("Failed to parse city JSON for %s: %s", self.city_id, err)
                    
        if not target_city:
            raise UpdateFailed(f"City {self.city_id} not found in forecast data")
            
        city_name = html.unescape(target_city.get("ciudad", self.city_name))
        fechasql = target_city.get("fechasql")
        
        # Parse forecast lists
        forecasts = []
        try:
            start_date = datetime.strptime(fechasql, "%Y-%m-%d")
        except (ValueError, TypeError):
            start_date = datetime.now()
            
        tope = target_city.get("tope", 5)
        temp_list = target_city.get("temperatura", [])
        tope = min(int(tope), len(temp_list))
        
        icono_list = target_city.get("icono", [])
        texto_list = target_city.get("texto", [])
        
        for i in range(tope):
            date_val = start_date + timedelta(days=i)
            
            temp_str = temp_list[i] if i < len(temp_list) else ""
            templow, temp = parse_temp_range(temp_str)
            
            day_icons = icono_list[i] if i < len(icono_list) else []
            if isinstance(day_icons, str):
                day_icons = [day_icons]
            condition = get_representative_condition(day_icons)
            
            day_texts = texto_list[i] if i < len(texto_list) else []
            if isinstance(day_texts, str):
                day_texts = [day_texts]
            unescaped_texts = [html.unescape(t) for t in day_texts if t]
            detailed_description = " / ".join(unescaped_texts)
            
            forecasts.append({
                "datetime": date_val.strftime("%Y-%m-%d"),
                "condition": condition,
                "native_temperature": temp,
                "native_templow": templow,
                "detailed_description": detailed_description,
            })
            
        # Rest of the day properties
        curr_icon = target_city.get("icono_resto_dia")
        current_condition = map_condition(curr_icon)
        
        curr_text = target_city.get("texto_resto_dia", "")
        current_text = html.unescape(curr_text) if curr_text else ""
        
        # Use first forecast day's temperature as current temperature fallback
        first_temp = None
        first_templow = None
        if forecasts:
            first_temp = forecasts[0]["native_temperature"]
            first_templow = forecasts[0]["native_templow"]
            
        result = {
            "city_id": self.city_id,
            "city_name": city_name,
            "condition": current_condition,
            "condition_text": current_text,
            "temperature": first_temp,
            "templow": first_templow,
            "forecast": forecasts,
            "redaccion": html.unescape(target_city.get("redaccion", "")),
        }
        
        return result
