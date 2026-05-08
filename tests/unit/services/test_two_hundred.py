from freezegun import freeze_time

from kodzu_thon.services.two_hundred import TwoHundredService


@freeze_time("2026-05-07 12:00:00")
def test_count_uses_api_data(mocker):
    fake_resp = mocker.Mock()
    fake_resp.json.return_value = {
        "data": {
            "stats": {"personnel_units": 900_000},
            "increase": {"personnel_units": 1000},
        }
    }
    mocker.patch("kodzu_thon.services.two_hundred.requests.get", return_value=fake_resp)

    svc = TwoHundredService()
    val = svc.count()
    assert val > 900_000
