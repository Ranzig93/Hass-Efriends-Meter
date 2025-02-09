import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.restore_state import RestoreEntity
from .const import * 

_LOGGER = logging.getLogger(__name__)

class EFriendsRawPowerSensor(SensorEntity, RestoreEntity):
    """Statischer Sensor für rawPowerMessage oder Trade-Daten (ohne Trader-ID)."""

    def __init__(self, hass, entry_id, unique_id, name, data_key, unit, data):
        self._hass = hass
        self._entry_id = entry_id
        self._unique_id = f"efriends_{unique_id}"
        self._name = name
        self._key = data_key
        self._unit = unit
        self._data = data
        self._state = 0.0
        _LOGGER.debug("EFriendsRawPowerSensor __init__: %s", self._unique_id)

    @property
    def device_info(self):
        device_info = {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": CONF_NAME,
            "manufacturer": CONF_MANUFACTURER,
            "model": CONF_MODEL,
            "sw_version": CONF_SW_VERSION,
        }
        _LOGGER.debug("Device Info: %s", device_info)
        return device_info

    @property
    def name(self):
        return self._name

    @property
    def unique_id(self):
        return self._unique_id

    @property
    def state(self):
        return self._state

    @property
    def unit_of_measurement(self):
        return self._unit

    def update_state_from_globaldata(self):
        val = self._data.get(self._key, 0.0)
        _LOGGER.debug("%s: update_state_from_globaldata() key=%s => %s", self._unique_id, self._key, val)
        self._state = round(val, 2)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old_state = await self.async_get_last_state()
        _LOGGER.debug("%s: async_added_to_hass => old_state=%s", self._unique_id, old_state)
        if old_state is not None:
            try:
                self._state = float(old_state.state)
                _LOGGER.debug("%s: restored state to %s", self._unique_id, self._state)
            except ValueError:
                pass

class EFriendsTraderBalanceSensor(SensorEntity, RestoreEntity):
    """Dynamische Entity pro Trader (Trader-ID), wird jetzt auch in JSON gespeichert."""

    def __init__(self, entry_id: str, trader_id: str, name: str, balance: float):
        self._entry_id = entry_id
        self._trader_id = trader_id
        self._name = name
        self._balance = balance
        _LOGGER.debug("EFriendsTraderBalanceSensor __init__: %s", self._trader_id)

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old_state = await self.async_get_last_state()
        if old_state is not None:
            try:
                self._balance = float(old_state.state)
            except ValueError:
                pass

    @property
    def device_info(self):
        device_info = {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": CONF_NAME,
            "manufacturer": CONF_MANUFACTURER,
            "model": CONF_MODEL,
            "sw_version": CONF_SW_VERSION,
        }
        _LOGGER.debug("Device Info: %s", device_info)
        return device_info

    @property
    def unique_id(self):
        return f"{self._entry_id}_efriends_trader_{self._trader_id}"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return round(self._balance, 2)

    @property
    def unit_of_measurement(self):
        return "balance"

    def set_balance(self, new_value: float):
        self._balance = new_value
        # Nur, wenn self.hass != None und entity_id != None, updaten
        if self.hass is not None and self.entity_id:
            self.schedule_update_ha_state()

class EFriendsConnectionStatusSensor(SensorEntity, RestoreEntity):
    """Sensor für den Verbindungsstatus des Geräts."""

    def __init__(self, entry_id: str, name: str):
        self._entry_id = entry_id
        self._name = name
        self._state = "Disconnected"  # Initialzustand
        _LOGGER.debug("EFriendsConnectionStatusSensor __init__: %s", self._entry_id)

    @property
    def device_info(self):
        device_info = {
            "identifiers": {(DOMAIN, self._entry_id)},
            "name": CONF_NAME,
            "manufacturer": CONF_MANUFACTURER,
            "model": CONF_MODEL,
            "sw_version": CONF_SW_VERSION,
        }
        _LOGGER.debug("Device Info: %s", device_info)
        return device_info

    @property
    def unique_id(self):
        return f"{self._entry_id}_efriends_connection_status"

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    def set_connection_status(self, is_connected: bool):
        """Setzt den Verbindungsstatus und aktualisiert den Zustand des Sensors."""
        self._state = "Connected" if is_connected else "Disconnected"
        if self.hass is not None and self.entity_id:
            self.schedule_update_ha_state()

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        old_state = await self.async_get_last_state()
        if old_state is not None:
            self._state = old_state.state