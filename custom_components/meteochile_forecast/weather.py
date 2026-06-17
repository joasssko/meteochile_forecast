"""Weather platform for MeteoChile."""
from __future__ import annotations

from homeassistant.components.weather import (
    Forecast,
    WeatherEntity,
    WeatherEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import MeteoChileCoordinator

async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up the weather platform from a config entry."""
    coordinator: MeteoChileCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([MeteoChileWeatherEntity(coordinator, entry)])

class MeteoChileWeatherEntity(CoordinatorEntity[MeteoChileCoordinator], WeatherEntity):
    """Representation of a MeteoChile Weather entity."""

    _attr_has_entity_name = True
    _attr_native_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator: MeteoChileCoordinator, entry: ConfigEntry) -> None:
        """Initialize the weather entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{coordinator.city_id}_weather"
        self._attr_name = None  # Using device name for entity name

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.city_id)},
            name=self.coordinator.city_name,
            manufacturer="MeteoChile",
            model="Weather Forecast",
        )

    @property
    def condition(self) -> str | None:
        """Return the current condition."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("condition")

    @property
    def native_temperature(self) -> float | None:
        """Return the temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("temperature")

    @property
    def native_templow(self) -> float | None:
        """Return the minimum temperature."""
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("templow")

    @property
    def supported_features(self) -> WeatherEntityFeature:
        """Filter supported features."""
        return WeatherEntityFeature.FORECAST_DAILY

    def _get_forecast_data(self) -> list[Forecast] | None:
        """Get the forecast data."""
        if not self.coordinator.data:
            return None
        
        raw_forecasts = self.coordinator.data.get("forecast", [])
        forecasts: list[Forecast] = []
        
        for item in raw_forecasts:
            forecasts.append(
                Forecast(
                    datetime=item["datetime"],
                    condition=item["condition"],
                    native_temperature=item["native_temperature"],
                    native_templow=item["native_templow"],
                    detailed_description=item["detailed_description"],
                )
            )
        return forecasts

    @property
    def forecast(self) -> list[Forecast] | None:
        """Return the daily forecast (legacy)."""
        return self._get_forecast_data()

    async def async_forecast_daily(self) -> list[Forecast] | None:
        """Return the daily forecast."""
        return self._get_forecast_data()

    @property
    def extra_state_attributes(self) -> dict[str, any]:
        """Return the extra state attributes."""
        attrs = {}
        if self.coordinator.data:
            attrs["redaccion"] = self.coordinator.data.get("redaccion")
            attrs["condition_text"] = self.coordinator.data.get("condition_text")
        return attrs
