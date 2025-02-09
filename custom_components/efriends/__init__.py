import logging
import socketio
import asyncio
import requests
from datetime import time
from .helper import * 
from .sensor_definition import * 

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.discovery import async_load_platform
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
    CONF_HOST,
    CONF_MODE,
    CONF_CONSUMPTION_ENTITY,
    CONF_API_KEY,
    DEFAULT_HOST
)

_LOGGER = logging.getLogger(__name__)

async def async_setup(hass: HomeAssistant, config: dict):
    """Optional: Setup via YAML (hier nicht genutzt, da config_flow=True)."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Wird aufgerufen, wenn der User die Integration hinzufügt.
    - Stellt Socket.IO-Verbindung her
    - Definiert Handler für rawPowerMessage und PeerTradingModuleSummaryEvent
    - Legt global_data an
    """
    _LOGGER.info("Setting up eFriends (entry_id=%s) with data=%s", entry.entry_id, entry.data)

    # Dictionary, in dem wir alle Daten ablegen
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    # Jede Instanz kann eigenständig sein
    hass.data[DOMAIN][entry.entry_id] = {}
    host = entry.data.get(CONF_HOST, DEFAULT_HOST)
    mode = entry.data.get(CONF_MODE, "read")
    consumption_entity = entry.data.get(CONF_CONSUMPTION_ENTITY, "")
    api_key = entry.data.get(CONF_API_KEY, "")

    hass.data[DOMAIN][entry.entry_id]["mode"] = mode;

    _LOGGER.info("E-Friends Setup: host=%s mode=%s", host, mode)

    if mode == "read":
        # Socket.IO-Reader
        reader = EFriendsSocketIOReader(hass, host)
        hass.data[DOMAIN][entry.entry_id]["socket_reader"] = reader
        await reader.async_init()

    else:
        # Http write
        writer = EFriendsWriter(hass, host, consumption_entity, api_key, entry.entry_id)
        hass.data[DOMAIN][entry.entry_id]["writer"] = writer
        await writer.async_init()

    # sensor.py
    hass.async_create_task(
        async_load_platform(hass, "sensor", DOMAIN, {"entry_id": entry.entry_id}, entry.data)
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:

    delete_traders_file(entry.entry_id)

    data = hass.data[DOMAIN].pop(entry.entry_id, None)
    if data:
        if "socket_reader" in data:
            await data["socket_reader"].async_unload()
        if "writer" in data:
            await data["writer"].async_unload()

    # Unload Sensor-Platform
    await hass.config_entries.async_unload_platforms(entry, ["sensor"])

    # Optionally: Daten aus hass.data entfernen
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


class EFriendsSocketIOReader:
    """Socket.IO Reader => rawPowerMessage, PeerTradingModuleSummaryEvent"""

    def __init__(self, hass: HomeAssistant, host: str):
        self._hass = hass
        self._host = host
        self._sio = socketio.Client()
        self._connected = False
        self._running = True

    async def async_init(self):
        # Registriere Events
        @self._sio.event
        def connect():
            _LOGGER.info("Mit eFriends Socket.IO verbunden")
            self._connected = True

        @self._sio.event
        def disconnect():
            _LOGGER.warning("Socket.IO (Reader) disconnected.")
            self._connected = False

        @self._sio.on("connect", namespace="/MeterDataAPI")
        def on_connect():
            _LOGGER.debug("Verbunden mit Namespace /MeterDataAPI")

        @self._sio.on("rawPowerMessage", namespace="/MeterDataAPI")
        def handle_raw_power(data):
            _LOGGER.debug("rawPowerMessage: %s", data)
            # HA-Event feuern
            self._hass.bus.fire("efriends_rawpower", data)

        @self._sio.on("PeerTradingModuleSummaryEvent")
        def handle_trading_data(data):
            _LOGGER.debug("PeerTradingModuleSummaryEvent: %s", data)
            self._hass.bus.fire("efriends_trading_update", data)

        # Socket-Connect asynchron (Executor)
        def _connect():
            try:
                _LOGGER.info(f"Verbinde zu ws://{self._host}/MeterDataAPI ...")
                self._sio.connect(f"ws://{self._host}")
                self._sio.emit('join', {}, namespace='/MeterDataAPI')

            except Exception as e:
                _LOGGER.error(f"Fehler beim Verbinden zu {self._host}: {e}")

        await self._hass.async_add_executor_job(_connect)

    async def async_unload(self):
        self._running = False
        _LOGGER.info("Socket.IO (Reader) unloading -> disconnect")
        self._sio.disconnect()

class EFriendsWriter:
    """Mittelwert bilden + HTTP-POST an http://<host>/v3/MeterDataAPI/MeterData mit api_key"""

    def __init__(self, hass: HomeAssistant, host: str, entity_id: str, api_key: str, status_entity_id: str):
        self._hass = hass
        self._host = host
        self._entity_id = entity_id
        self._api_key = api_key
        self._sum_values = 0.0
        self._count = 0
        self._interval = 5
        self._unsub_listener = None
        self._loop_task = None
        self._status_entity_id = status_entity_id
        self._connection_status = False  # Initialer Status: Verbindung nicht aktiv

    async def async_init(self):
        self._unsub_listener = self._hass.bus.async_listen("state_changed", self._handle_state_change)
        self._loop_task = self._hass.loop.create_task(self._loop_cycle())


    def _handle_state_change(self, event):
        if not event.data:
            return
        if event.data.get("entity_id") == self._entity_id:
            new_state = event.data["new_state"]
            if new_state and new_state.state not in (None, ""):
                try:
                    val = float(new_state.state)
                    self._sum_values += val
                    self._count += 1
                except ValueError:
                    pass

    def _send_data(self, url, data, headers):
        # Diese Funktion läuft im Threadpool (Blockierung erlaubt)
        response = requests.post(url, json=data, headers=headers, timeout=5)
        return response

    async def _loop_cycle(self):
        import requests
        url = f"http://{self._host}/v3/MeterDataAPI/MeterData"
        while True:
            _LOGGER.info("asyncio.sleep")
            await asyncio.sleep(self._interval)
            if self._count > 0:
                avg_val = round(self._sum_values / self._count)
                self._sum_values = 0.0
                self._count = 0
                data = {
                    "power1Watt": avg_val,
                    "power2Watt": 0,
                    "power3Watt": 0,
                    "powerTotal": avg_val,
                    "voltage1Volt": 230,
                    "voltage2Volt": 230,
                    "voltage3Volt": 230,
                    "dataSource": "HA E-Friends Writer"
                }
                headers = {
                    "Content-Type": "application/json",
                    "apiKey": self._api_key
                }
                try:
                    # async_add_executor_job => blockierende Funktion in Threadpool verschieben
                    resp = await self._hass.async_add_executor_job(
                        self._send_data, url, data, headers
                    )

                    if resp.status_code == 200:
                        _LOGGER.info("Daten an %s gesendet: %s", url, resp.text)
                        self._hass.bus.fire("efriends_write_status", True)
                    else:
                        _LOGGER.warning("Send-Fehler: %s - %s", resp.status_code, resp.text)
                        self._hass.bus.fire("efriends_write_status", False)
                except Exception as e:
                    _LOGGER.error("Exception beim Senden an %s: %s", url, e)
                    self._hass.bus.fire("efriends_write_status", False)

    async def async_unload(self):
        if self._unsub_listener:
            self._unsub_listener()
        if self._loop_task:
            self._loop_task.cancel()