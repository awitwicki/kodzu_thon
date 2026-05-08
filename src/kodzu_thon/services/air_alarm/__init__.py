from kodzu_thon.services.air_alarm.ajax_api import (
    STATE_LIBRARY,
    fetch_alarm_states,
)
from kodzu_thon.services.air_alarm.geojson import parse_geojson_data
from kodzu_thon.services.air_alarm.renderer import render_alarm_map

__all__ = ["STATE_LIBRARY", "AirAlarmService"]


class AirAlarmService:
    def __init__(self, geojson_path: str, img_dir: str = "img"):
        self.districts = parse_geojson_data(geojson_path)
        self._img_dir = img_dir

    def fetch_alarms(self) -> dict[str, bool]:
        return fetch_alarm_states()

    def render(self, alarms: dict[str, bool]) -> str:
        return render_alarm_map(self.districts, alarms, img_dir=self._img_dir)
