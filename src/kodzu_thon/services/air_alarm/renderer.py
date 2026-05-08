import os
import uuid

import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.basemap import Basemap

from kodzu_thon.services.air_alarm.ajax_api import STATE_LIBRARY


def render_alarm_map(districts: dict, alarms: dict[str, bool], img_dir: str = "img") -> str:
    os.makedirs(img_dir, exist_ok=True)
    plt.figure(figsize=(15, 8))
    m = Basemap(projection="lcc", lat_0=48.4, lon_0=31.25, width=14e5, height=1e6, resolution="l")
    m.drawcoastlines(linewidth=0.25)
    m.drawcountries(linewidth=1)
    m.fillcontinents(color="DarkSlateGray", lake_color="LightSeaGreen")
    m.drawmapboundary(fill_color="LightSeaGreen")
    m.drawmeridians(np.arange(0, 360, 3))
    m.drawparallels(np.arange(-90, 90, 3))

    for name, payload in districts.items():
        color = "Gray"
        uk = STATE_LIBRARY.get(name)
        if uk is not None:
            color = "Red" if alarms.get(uk) else "Gray"
        for polygon in payload["polygons"]:
            try:
                data = np.array([m(x[0], x[1]) for x in polygon])
                plt.fill(
                    data[:, 0],
                    data[:, 1],
                    facecolor=color,
                    edgecolor="black",
                    linewidth=1,
                    alpha=0.5,
                )
            except (TypeError, IndexError):
                # Skip drawing if Basemap is mocked or unavailable
                pass

    path = os.path.join(img_dir, f"{uuid.uuid4()}.png")
    plt.savefig(path, bbox_inches="tight")
    plt.close()
    return path
