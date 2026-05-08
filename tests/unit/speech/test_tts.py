from kodzu_thon.speech.tts import synthesize_mp3


def test_synthesize_writes_mp3(mocker, tmp_path):
    fake_obj = mocker.Mock()
    mocker.patch("kodzu_thon.speech.tts.gTTS", return_value=fake_obj)

    out = synthesize_mp3("hello", media_dir=str(tmp_path))

    assert out.endswith(".mp3")
    assert str(tmp_path) in out
    fake_obj.save.assert_called_once_with(out)
