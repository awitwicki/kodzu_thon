from kodzu_thon.services.air_alarm.ajax_api import fetch_alarm_states


def test_fetch_returns_alarm_dict_keyed_by_uk_name(mocker):
    fake = mocker.Mock()
    fake.json.return_value = {
        "regions": [
            {"name": "Київська область", "regionType": "STATE", "alarmsInRegion": [{"a": 1}]},
            {"name": "Львівська область", "regionType": "STATE", "alarmsInRegion": []},
            {"name": "Some city", "regionType": "CITY", "alarmsInRegion": [{"a": 1}]},
        ]
    }
    mocker.patch("kodzu_thon.services.air_alarm.ajax_api.requests.get", return_value=fake)

    out = fetch_alarm_states()
    assert out["Київська область"] is True
    assert out["Львівська область"] is False
    assert "Some city" not in out
