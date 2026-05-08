import json

import numpy as np


def parse_geojson_data(path: str) -> dict:
    with open(path) as f:
        geojson = json.load(f)

    districts = {}
    for feature in geojson["features"]:
        polygons = feature["geometry"]["coordinates"]
        polygons = [np.array(p, dtype=np.float16) for p in polygons]
        districts[feature["properties"]["name"]] = {"polygons": polygons}
    return districts
