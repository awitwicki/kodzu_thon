import sys

from influxdb import InfluxDBClient


class InfluxWriter:
    def __init__(self, host: str, port: int, db: str):
        self._client = InfluxDBClient(host=host, port=port)
        self._client.switch_database(db)

    def write(self, tags: dict, fields: dict) -> None:
        try:
            self._client.write_points(
                [
                    {
                        "measurement": "bots",
                        "tags": tags,
                        "fields": fields,
                    }
                ]
            )
        except Exception as e:
            print(f"influx write failed: {e}", file=sys.stderr)
