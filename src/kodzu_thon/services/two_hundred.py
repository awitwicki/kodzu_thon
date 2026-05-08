import datetime

import cachetools.func
import requests


class TwoHundredService:
    _STARTED = datetime.datetime(2022, 2, 24)
    _URL = "https://russianwarship.rip/api/v1/statistics/latest"

    @cachetools.func.ttl_cache(maxsize=1, ttl=60 * 60)
    def _get_stat(self) -> dict:
        return requests.get(self._URL).json()

    def count(self) -> float:
        stat = self._get_stat()["data"]
        last_value = stat["stats"]["personnel_units"]
        last_increase = stat["increase"]["personnel_units"]

        last_date = datetime.datetime.combine(datetime.date.today(), datetime.datetime.min.time())
        total_days = (last_date - self._STARTED).days
        days_delta = (datetime.datetime.utcnow() - last_date).days
        average = last_value / max(total_days, 1)

        now = datetime.datetime.utcnow() + datetime.timedelta(hours=2)
        seconds_today = (
            now - datetime.datetime.combine(now.date(), datetime.time())
        ).total_seconds()
        today_pct = seconds_today / 86400.0
        return last_value + last_increase * today_pct + average * days_delta
