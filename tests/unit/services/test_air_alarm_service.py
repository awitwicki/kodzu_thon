from pathlib import Path

from kodzu_thon.services.air_alarm import AirAlarmService

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "ukraine_minimal.geojson"


def test_service_loads_districts_at_init():
    svc = AirAlarmService(str(FIXTURE))
    assert "Kiev Oblast" in svc.districts


def test_service_render_delegates(mocker):
    svc = AirAlarmService(str(FIXTURE))
    spy = mocker.patch("kodzu_thon.services.air_alarm.render_alarm_map", return_value="img/x.png")
    out = svc.render({"Київська область": True})
    assert out == "img/x.png"
    spy.assert_called_once()


def test_service_fetch_delegates(mocker):
    svc = AirAlarmService(str(FIXTURE))
    spy = mocker.patch(
        "kodzu_thon.services.air_alarm.fetch_alarm_states", return_value={"Київська область": True}
    )
    assert svc.fetch_alarms() == {"Київська область": True}
    spy.assert_called_once()
