import json
import os
import logging
from .helper import * 
from .sensor_definition import * 
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfElectricCurrent,
)

from .const import DOMAIN, TRADERS_FILE_PATH
_LOGGER = logging.getLogger(__name__)

SENSOR_DEFINITIONS = [
    ("power_total",   "Power Total",    "powerTotal",        UnitOfPower.WATT),
    ("power_l1",      "Power L1",       "power1Watt",        UnitOfPower.WATT),
    ("power_l2",      "Power L2",       "power2Watt",        UnitOfPower.WATT),
    ("power_l3",      "Power L3",       "power3Watt",        UnitOfPower.WATT),
    ("current_l1",    "Current L1",     "current1Ampere",    UnitOfElectricCurrent.AMPERE),
    ("current_l2",    "Current L2",     "current2Ampere",    UnitOfElectricCurrent.AMPERE),
    ("current_l3",    "Current L3",     "current3Ampere",    UnitOfElectricCurrent.AMPERE),
    ("voltage_l1",    "Voltage L1",     "voltage1Volt",      UnitOfElectricPotential.VOLT),
    ("voltage_l2",    "Voltage L2",     "voltage2Volt",      UnitOfElectricPotential.VOLT),
    ("voltage_l3",    "Voltage L3",     "voltage3Volt",      UnitOfElectricPotential.VOLT),
    ("today_wh",      "Today (Wh)",     "todayWatt",         UnitOfEnergy.WATT_HOUR),
    ("today_kwh",     "Today (kWh)",    "today",             UnitOfEnergy.KILO_WATT_HOUR),
    ("yesterday_kwh", "Yesterday (kWh)","yesterday",         UnitOfEnergy.KILO_WATT_HOUR)
]

SENSOR_DEFINITIONS_TRADE = [
    ("energyBalance",           "Energy Balance",           "energyBalance",          UnitOfPower.WATT),
    ("totalOrderVolume",        "Total Order Volume",       "totalOrderVolume",       UnitOfPower.WATT),
    ("consumable",              "Consumable",               "consumable",             UnitOfPower.WATT),
    ("remainingEnergyBalance",  "Remaining Energy Balance", "remainingEnergyBalance", UnitOfPower.WATT)
]

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Von __init__.py via async_load_platform("sensor", DOMAIN, {}, {}) aufgerufen."""
    if not discovery_info:
        return

    entry_id = discovery_info.get("entry_id")
    _LOGGER.info("async_setup_platform: Erhaltenes entry_id = %s", entry_id)
    _LOGGER.debug("hass.data[DOMAIN] keys = %s", hass.data[DOMAIN].keys())

    data = hass.data[DOMAIN].get(entry_id)
    if not data:
        # Möglicherweise noch nicht angelegt in __init__?
        data = {}
        hass.data[DOMAIN][entry_id] = data

    data = hass.data[DOMAIN][entry_id]


    # Read Mode
    if data["mode"] == "read":
        if "global_data" not in data:
            data["global_data"] = {
                # Normale Sensorwerte
                "powerTotal": 0.0,
                "power1Watt": 0.0,
                "power2Watt": 0.0,
                "power3Watt": 0.0,
                "current1Ampere": 0.0,
                "current2Ampere": 0.0,
                "current3Ampere": 0.0,
                "voltage1Volt": 0.0,
                "voltage2Volt": 0.0,
                "voltage3Volt": 0.0,
                "todayWatt": 0.0,
                "today": 0.0,
            }
        if "trade_data" not in data:
            data["trade_data"] = {
                # Normale Sensorwerte
                "energyBalance": 0.0,
                "totalOrderVolume": 0.0,
                "consumable": 0.0,
                "remainingEnergyBalance": 0.0,

                # Trader-Daten (dynamische Sensoren)
                "traders": {}
            }
        

        global_data = data["global_data"]
        trade_data = data["trade_data"]


        # 1) Trader aus JSON laden und in trade_data["traders"] übernehmen
        persistent_traders = load_traders_from_json(entry_id)
        if persistent_traders:
            _LOGGER.info("Gefundene Trader aus JSON: %s", persistent_traders)
            trade_data["traders"].update(persistent_traders)
        else:
            _LOGGER.info("Keine Trader in %s gefunden.", TRADERS_FILE_PATH)

        # 2) Statische Global-Sensoren erstellen
        static_sensors = []
        for uid, name, key, unit in SENSOR_DEFINITIONS:
            unique_id_final = f"{entry_id}_{uid}"
            static_sensors.append(
                EFriendsRawPowerSensor(
                    hass,
                    entry_id,
                    unique_id_final,
                    name,
                    key,
                    unit,
                    global_data
                )
            )

        # 3) Statische Trade-Sensoren
        static_trade_sensors = []
        for uid, name, key, unit in SENSOR_DEFINITIONS_TRADE:
            unique_id_final = f"{entry_id}_{uid}"
            static_trade_sensors.append(
                EFriendsRawPowerSensor(
                    hass,
                    entry_id,
                    unique_id_final,
                    name,
                    key,
                    unit,
                    trade_data
                )
            )

        # 4) Dynamische Trader-Sensoren
        if "trader_sensors" not in data:
            data["trader_sensors"] = {}
        trader_sensors = data["trader_sensors"]

        # async_add_entities-Callback sichern
        data["async_add_entities"] = async_add_entities

        # Ggf. manuelles Anstoßen
        #_update_trader_sensors(hass, entry_id, static_trade_sensors)


        # Statische Sensoren an HA übergeben
        async_add_entities(static_sensors, update_before_add=True)
        async_add_entities(static_trade_sensors, update_before_add=True)

        # Event-Listener registrieren -> hier findet die eigentliche Datenverarbeitung statt
        # a) rawPower
        def handle_rawpower_event(event):
            """Verarbeitet das Event 'efriends_rawpower' und aktualisiert global_data."""
            event_data = event.data
            _LOGGER.debug("handle_rawpower_event: %s", event_data)

            # Hier wie früher:
            global_data["powerTotal"]    = float(event_data.get("powerTotal", 0.0))
            global_data["power1Watt"]    = float(event_data.get("power1Watt", 0.0))
            global_data["power2Watt"]    = float(event_data.get("power2Watt", 0.0))
            global_data["power3Watt"]    = float(event_data.get("power3Watt", 0.0))
            global_data["current1Ampere"] = float(event_data.get("current1Ampere", 0.0))
            global_data["current2Ampere"] = float(event_data.get("current2Ampere", 0.0))
            global_data["current3Ampere"] = float(event_data.get("current3Ampere", 0.0))
            global_data["voltage1Volt"]   = float(event_data.get("voltage1Volt", 0.0))
            global_data["voltage2Volt"]   = float(event_data.get("voltage2Volt", 0.0))
            global_data["voltage3Volt"]   = float(event_data.get("voltage3Volt", 0.0))

            # Tageswerte hochrechnen
            global_data["todayWatt"] += abs(global_data["powerTotal"]) / 1800.0
            global_data["today"] = global_data["todayWatt"] / 1000.0

            # Anschließend unsere statischen Sensoren updaten
            _update_static_sensors(static_sensors)

        unsub1 = hass.bus.async_listen("efriends_rawpower", handle_rawpower_event)
        data["unsub_rawpower"] = unsub1

        # b) trading_update
        async def handle_trading_event(event):
            """Verarbeitet das Event 'efriends_trading_update' und aktualisiert trade_data."""
            event_data = event.data
            _LOGGER.debug("handle_trading_event: %s", event_data)

            # Normale Felder
            trade_data["energyBalance"]          = float(event_data.get("energyBalance", 0.0))
            trade_data["totalOrderVolume"]       = float(event_data.get("totalOrderVolume", 0.0))
            trade_data["consumable"]             = float(event_data.get("consumable", 0.0))
            trade_data["remainingEnergyBalance"] = float(event_data.get("remainingEnergyBalance", 0.0))

            # Traders verarbeiten
            confirmed_orders = event_data.get("confirmedOrders", [])
            traders_dict = trade_data["traders"]
            for co in confirmed_orders:
                seller_id = str(co.get("sellerId"))
                buyer_id  = str(co.get("buyerId"))
                amount    = float(co.get("amount", 0))

                if seller_id not in traders_dict:
                    traders_dict[seller_id] = 0.0
                if buyer_id not in traders_dict:
                    traders_dict[buyer_id] = 0.0

                # Bsp: Seller = amount, Buyer = amount
                traders_dict[seller_id] = amount
                traders_dict[buyer_id]  = amount

            # Jetzt dynamische Trader-Sensoren anlegen/updaten
            await _update_trader_sensors(hass, entry_id, static_trade_sensors)

        unsub2 = hass.bus.async_listen("efriends_trading_update", handle_trading_event)
        data["unsub_trading_update"] = unsub2

        # Falls du direkt nach dem Laden vorhandene Trader-Sensoren anlegen willst
        _LOGGER.debug("Starte _update_trader_sensors, um persistierte Trader zu berücksichtigen.")
        await _update_trader_sensors(hass, entry_id, static_trade_sensors)

    # Write Mode
    else:
         # Erstelle den Verbindungsstatus-Sensor
        connection_sensor = EFriendsConnectionStatusSensor(
            entry_id=entry_id,
            name="E-Friends Connection Status"
        )

        # Statische Sensoren an HA übergeben
        async_add_entities([connection_sensor], update_before_add=True)

        # Event-Listener registrieren -> hier findet die eigentliche Datenverarbeitung statt
        def handle_write_status_event(event):
            """Verarbeitet das Event 'efriends_write_status' und aktualisiert global_data."""
            event_data = event.data
            _LOGGER.debug("handle_write_status_event: %s", event_data)

            # Anschließend unsere statischen Sensoren updaten
            #_update_static_sensors([connection_sensor])
            if connection_sensor.hass:
                connection_sensor.schedule_update_ha_state()

        unsub3 = hass.bus.async_listen("efriends_write_status", handle_write_status_event)
        data["unsub_write_status"] = unsub3


def _update_static_sensors(sensors):
    """Aktualisiert statische Sensoren (rawPower oder Trade-Sensoren)."""
    for sensor in sensors:
        if sensor.hass:
            sensor.update_state_from_globaldata()
            sensor.schedule_update_ha_state()

async def _update_trader_sensors(hass, entry_id, static_trade_sensors):
    """Erzeugt / aktualisiert Trader-Sensoren und speichert sie in JSON."""
    _LOGGER.debug("hass.data[DOMAIN] keys = %s", entry_id)
    data = hass.data[DOMAIN][entry_id]
    trade_data = data["trade_data"]
    trader_sensors = data["trader_sensors"]
    async_add_entities = data["async_add_entities"]

    # 1) Aktuelle Trader-Daten aus trade_data lesen
    traders_dict = trade_data.get("traders", {})
    _LOGGER.debug("_update_trader_sensors %s", traders_dict)

    new_entities = []

    # 2) Neue/aktualisierte Trader-Sensoren anlegen oder updaten
    for trader_id, balance in traders_dict.items():
        if trader_id not in trader_sensors:
            _LOGGER.debug("EFriendsTraderBalanceSensor %s", trader_id)
            sensor = EFriendsTraderBalanceSensor(
                entry_id, trader_id, f"Trader {trader_id}", balance
            )
            trader_sensors[trader_id] = sensor
            new_entities.append(sensor)
        else:
            sensor = trader_sensors[trader_id]
            sensor.set_balance(balance)

    # 3) Trader-Sensoren prüfen, die diesmal keine Daten erhalten haben
    #    -> Falls der letzte Balancewert > 0 ist, auf 0 setzen
    for existing_trader_id, existing_sensor in trader_sensors.items():
        if existing_trader_id not in traders_dict:
            # Keine neuen Daten => Balance ggf. auf 0 zurücksetzen
            if existing_sensor._balance > 0:  # oder existing_sensor.balance > 0, je nach Implementierung
                existing_sensor.set_balance(0)

    if new_entities:
        async_add_entities(new_entities, update_before_add=True)
        # **WICHTIG**: traders_dict in JSON speichern
        await async_save_traders_to_json(hass, traders_dict,entry_id)

    # 2) Update bestehender Trader-Sensoren
    for sensor in trader_sensors.values():
        if sensor.hass:
            sensor.schedule_update_ha_state()

    # 3) Statische Trade-Sensoren updaten
    for sensor in static_trade_sensors:
        if sensor.hass:
            sensor.update_state_from_globaldata()
            sensor.schedule_update_ha_state()

    


