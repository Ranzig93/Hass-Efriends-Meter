import json
import os
import logging

from homeassistant.core import HomeAssistant
from .const import TRADERS_FILE_PATH

_LOGGER = logging.getLogger(__name__)

def load_traders_from_json(entry_id: str) -> dict:
    """Trader-Daten (traders) aus JSON-Datei laden (synchron)."""
    filePath = os.path.join(TRADERS_FILE_PATH, f"{entry_id}_trader.json")
    _LOGGER.debug("load_traders_from_json %s", filePath)

    if not os.path.isfile(filePath):
        return {}

    try:
        with open(filePath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                _LOGGER.debug("load_traders_from_json success: %s", data)
                return data
    except Exception as e:
        _LOGGER.warning("Fehler beim Laden von %s: %s", filePath, e)
    return {}

def _save_traders_sync(filePath: str, traders_dict: dict):
    """Synchroner Datei-Schreibvorgang (wird im Executor ausgeführt)."""
    directory = os.path.dirname(filePath)
    os.makedirs(directory, exist_ok=True)
    with open(filePath, "w", encoding="utf-8") as f:
        json.dump(traders_dict, f, ensure_ascii=False, indent=2)

async def async_save_traders_to_json(hass: HomeAssistant, traders_dict: dict, entry_id: str) -> None:
    """
    Trader-Daten (traders) in JSON-Datei speichern,
    aber nicht blockierend im Eventloop.
    """
    filePath = os.path.join(TRADERS_FILE_PATH, f"{entry_id}_trader.json")
    _LOGGER.debug("async_save_traders_to_json => %s", filePath)
    
    try:
        await hass.async_add_executor_job(_save_traders_sync, filePath, traders_dict)
    except Exception as e:
        _LOGGER.error("Fehler beim Schreiben nach %s: %s", filePath, e)

def delete_traders_file(entry_id: str) -> None:
    """Die zugehörige Datei löschen (synchron, ggf. im Executor ausführen)."""
    filePath = os.path.join(TRADERS_FILE_PATH, f"{entry_id}_trader.json")
    try:
        if os.path.exists(filePath):
            os.remove(filePath)
            _LOGGER.info("Datei %s erfolgreich gelöscht.", filePath)
        else:
            _LOGGER.warning("Datei %s existiert nicht.", filePath)
    except Exception as e:
        _LOGGER.error("Fehler beim Löschen der Datei %s: %s", filePath, e)
