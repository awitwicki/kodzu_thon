from kodzu_thon.speech.waveform import get_waveform


def test_get_waveform_length_and_bounds():
    wf = get_waveform(0, 31, 100)
    assert len(wf) == 100
    assert all(0 <= x < 31 for x in wf)


def test_get_waveform_zero_count():
    assert get_waveform(0, 31, 0) == []
