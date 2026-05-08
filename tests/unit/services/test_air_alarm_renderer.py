import numpy as np

from kodzu_thon.services.air_alarm.renderer import render_alarm_map


def _districts():
    return {"Kiev Oblast": {"polygons": [np.array([[30, 50], [31, 51]], dtype=np.float16)]}}


def test_render_writes_png_and_returns_path(mocker, tmp_path):
    save = mocker.patch("kodzu_thon.services.air_alarm.renderer.plt.savefig")
    mocker.patch("kodzu_thon.services.air_alarm.renderer.plt.figure")
    mocker.patch("kodzu_thon.services.air_alarm.renderer.plt.fill")
    mocker.patch("kodzu_thon.services.air_alarm.renderer.plt.close")
    mocker.patch("kodzu_thon.services.air_alarm.renderer.Basemap")

    path = render_alarm_map(_districts(), {"Київська область": True}, img_dir=str(tmp_path))

    assert path.startswith(str(tmp_path))
    assert path.endswith(".png")
    save.assert_called_once()
