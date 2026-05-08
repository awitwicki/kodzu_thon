from pathlib import Path

import numpy as np

from kodzu_thon.services.air_alarm.geojson import parse_geojson_data

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "ukraine_minimal.geojson"


def test_parse_returns_districts_keyed_by_name():
    districts = parse_geojson_data(str(FIXTURE))
    assert "Kiev Oblast" in districts
    assert "Lviv Oblast" in districts


def test_parse_polygons_are_numpy_arrays():
    districts = parse_geojson_data(str(FIXTURE))
    polys = districts["Kiev Oblast"]["polygons"]
    assert isinstance(polys, list)
    assert isinstance(polys[0], np.ndarray)
    assert polys[0].shape[1] == 2
