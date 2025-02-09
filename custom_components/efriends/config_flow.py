import logging
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_MODE,
    CONF_CONSUMPTION_ENTITY,
    CONF_API_KEY,
)

_LOGGER = logging.getLogger(__name__)

class EFriendsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config Flow für die E-Friends Integration mit Unique ID (IP)."""

    VERSION = 1

    def __init__(self):
        self.temp_host = None
        self.temp_mode = None
        self.temp_api_key = None
        self.temp_entity = None

    async def async_step_user(self, user_input=None):
        """
        Schritt 1: IP/Host abfragen.
        Setze die Unique ID = IP. Falls schon vorhanden => Abbruch.
        """
        errors = {}

        if user_input is not None:
            host = user_input["host"].strip()

            # Unique ID = IP
            await self.async_set_unique_id(host)
            self._abort_if_unique_id_configured()

            self.temp_host = host
            return await self.async_step_mode()

        data_schema = vol.Schema({
            vol.Required("host", default="192.168.0.100"): cv.string
        })
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )
    
    
    async def async_step_mode(self, user_input=None):
        """
        Schritt 2: read/write.
        - read => Direkt Entry
        - write => Weiter zu write_api_key
        """
        errors = {}
        if user_input is not None:
            selected_mode = user_input["mode"]
            if selected_mode == "read":
                # Direkt
                return self.async_create_entry(
                    title=f"E-Friends Read {self.temp_host}",
                    data={
                        CONF_HOST: self.temp_host,
                        CONF_MODE: "read"
                    }
                )
            else:
                # => write
                self.temp_mode = "write"
                return await self.async_step_write_settings()

        data_schema = vol.Schema({
            vol.Required("mode", default="read"): vol.In(["read", "write"])
        })
        return self.async_show_form(
            step_id="mode",
            data_schema=data_schema,
            errors=errors
        )
    

    async def async_step_write_settings(self, user_input=None):
        """Beispiel: DropDown-Auswahl einer vorhandenen Sensor-Entity."""
        errors = {}

        if user_input is not None:
            self.temp_api_key = user_input["api_key"]
            self.temp_entity = user_input["consumption_entity"]

            return self.async_create_entry(
                title=f"E-Friends Write {self.temp_host}",
                data={
                    CONF_HOST: self.temp_host,
                    CONF_MODE: "write",
                    CONF_CONSUMPTION_ENTITY: self.temp_entity,
                    CONF_API_KEY: self.temp_api_key
                }
            )

        # 1) Hole das Entity-Registry
        ent_reg = er.async_get(self.hass)
        sensor_entities = []
        for entity_id, entry in ent_reg.entities.items():
            if entry.domain == "sensor":
                # Prüfe im Zustand, ob unit_of_measurement == "W"
                state_obj = self.hass.states.get(entry.entity_id)
                if state_obj:
                    uom = state_obj.attributes.get("unit_of_measurement")
                    if uom == "W":  # oder "Watt"
                        sensor_entities.append(entry.entity_id)

            data_schema = vol.Schema({
                vol.Required("api_key"): cv.string,
                vol.Required("consumption_entity"): vol.In(sensor_entities)
            })

        return self.async_show_form(
            step_id="write_settings",
            data_schema=data_schema,
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EFriendsOptionsFlow(config_entry)

class EFriendsOptionsFlow(config_entries.OptionsFlow):
    """Optionale Einstellungen."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return self.async_create_entry(title="EFriends Options", data={})
