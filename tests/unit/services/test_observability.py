from kodzu_thon.services.observability import InfluxWriter


def test_writer_writes_point(mocker):
    fake_client = mocker.Mock()
    mocker.patch("kodzu_thon.services.observability.InfluxDBClient", return_value=fake_client)

    w = InfluxWriter("host", 8086, "bots")
    w.write({"botname": "kodzuthon"}, {"income_messages": 1.0})

    fake_client.switch_database.assert_called_once_with("bots")
    fake_client.write_points.assert_called_once_with(
        [
            {
                "measurement": "bots",
                "tags": {"botname": "kodzuthon"},
                "fields": {"income_messages": 1.0},
            }
        ]
    )


def test_writer_swallows_errors(mocker):
    fake_client = mocker.Mock()
    fake_client.write_points.side_effect = RuntimeError("influx down")
    mocker.patch("kodzu_thon.services.observability.InfluxDBClient", return_value=fake_client)

    w = InfluxWriter("host", 8086, "bots")
    w.write({}, {"x": 1.0})  # no exception
